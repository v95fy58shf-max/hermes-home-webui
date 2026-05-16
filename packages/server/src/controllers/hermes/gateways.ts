import { execFile } from 'child_process'
import { existsSync } from 'fs'
import { mkdir, writeFile } from 'fs/promises'
import { join } from 'path'
import { promisify } from 'util'
import { getGatewayManagerInstance } from '../../services/gateway-bootstrap'
import { detectHermesRootHome, getHermesBin } from '../../services/hermes/hermes-path'
import { safeFileStore } from '../../services/safe-file-store'

const execFileAsync = promisify(execFile)
const PROFILE_NAME_RE = /^[a-z0-9][a-z0-9_-]{1,31}$/
const HOME_MASTER_PROFILE = process.env.HERMES_HOME_MASTER_PROFILE || 'home-master'
const HOME_MASTER_INCOMING_URL = process.env.HERMES_HOME_MASTER_URL || 'http://127.0.0.1:18080/incoming'
const HOME_CONFIG_PATH = process.env.HERMES_HOME_CONFIG || '/opt/hermes-home/config.yaml'
const CHANNEL_SECTIONS = [
  'telegram', 'discord', 'slack', 'whatsapp', 'matrix',
  'weixin', 'wecom', 'feishu', 'dingtalk', 'qqbot',
]
const CHANNEL_ENV_KEYS = [
  'TELEGRAM_BOT_TOKEN',
  'DISCORD_BOT_TOKEN',
  'SLACK_BOT_TOKEN',
  'MATRIX_ACCESS_TOKEN',
  'MATRIX_HOMESERVER',
  'FEISHU_APP_ID',
  'FEISHU_APP_SECRET',
  'DINGTALK_CLIENT_ID',
  'DINGTALK_CLIENT_SECRET',
  'DINGTALK_APP_KEY',
  'DINGTALK_ALLOWED_USERS',
  'DINGTALK_ALLOW_ALL_USERS',
  'QQ_APP_ID',
  'QQ_CLIENT_SECRET',
  'QQ_ALLOWED_USERS',
  'QQ_ALLOW_ALL_USERS',
  'WECOM_BOT_ID',
  'WECOM_SECRET',
  'WEIXIN_TOKEN',
  'WEIXIN_ACCOUNT_ID',
  'WEIXIN_BASE_URL',
  'WHATSAPP_ENABLED',
]

const RELAY_PLUGIN_YAML = `name: home-slave-relay
version: 0.1.0
description: "Relay slave gateway messages to the local Hermes Home master gateway."
hooks:
  - pre_gateway_dispatch
`

const RELAY_PLUGIN_PY = `from __future__ import annotations

import json
import os
import urllib.request


MASTER_URL = os.getenv("HERMES_HOME_MASTER_URL", "http://127.0.0.1:18080/incoming")
GATEWAY_ID = os.getenv("HERMES_HOME_GATEWAY_ID", "home-slave")
MEMBER_ID = os.getenv("HERMES_HOME_MEMBER_ID", GATEWAY_ID)


def _source_to_dict(source):
    platform = getattr(source, "platform", None)
    if hasattr(platform, "value"):
        platform = platform.value
    return {
        "platform": platform or "",
        "user_id": getattr(source, "user_id", "") or "",
        "chat_id": getattr(source, "chat_id", "") or "",
        "user_name": getattr(source, "user_name", "") or "",
        "chat_type": getattr(source, "chat_type", "") or "",
    }


def relay_to_master(**kwargs):
    event = kwargs.get("event")
    if event is None:
        return {"action": "allow"}
    text = getattr(event, "text", "") or ""
    if not text.strip():
        return {"action": "allow"}

    payload = {
        "gateway_id": GATEWAY_ID,
        "member_id": MEMBER_ID,
        "message_id": getattr(event, "message_id", "") or "",
        "text": text,
        "source": _source_to_dict(getattr(event, "source", None)),
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        MASTER_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            if 200 <= response.status < 300:
                return {"action": "skip", "reason": "relayed-to-home-master"}
    except Exception:
        return {"action": "allow"}
    return {"action": "allow"}


def register(ctx):
    ctx.register_hook("pre_gateway_dispatch", relay_to_master)
`

function normalizeProfileName(name?: string): string {
  return String(name || '').trim().toLowerCase()
}

function profileDir(root: string, name: string): string {
  return name === 'default' ? root : join(root, 'profiles', name)
}

function createCliEnv(root: string): NodeJS.ProcessEnv {
  return {
    ...process.env,
    HERMES_HOME: root,
  }
}

async function suggestProfileName(existingProfiles: string[]): Promise<string> {
  const taken = new Set(existingProfiles)
  let max = 2
  for (const profile of existingProfiles) {
    const match = profile.match(/^wechat(\d+)$/)
    if (match) max = Math.max(max, Number(match[1]))
  }
  let candidate = `wechat${max + 1}`
  while (taken.has(candidate)) {
    max += 1
    candidate = `wechat${max + 1}`
  }
  return candidate
}

async function installRelayPlugin(dir: string): Promise<void> {
  const pluginDir = join(dir, 'plugins', 'home_slave_relay')
  await mkdir(pluginDir, { recursive: true })
  await writeFile(join(pluginDir, 'plugin.yaml'), RELAY_PLUGIN_YAML, 'utf-8')
  await writeFile(join(pluginDir, '__init__.py'), RELAY_PLUGIN_PY, 'utf-8')
}

async function configureRelayEnv(dir: string, name: string): Promise<void> {
  await safeFileStore.updateText(join(dir, '.env'), (current) => {
    const kept = current
      .split(/\r?\n/)
      .filter(line => !/^\s*HERMES_HOME_(GATEWAY_ID|MEMBER_ID|MASTER_URL)\s*=/.test(line))
      .filter((line, index, lines) => line.trim() || index < lines.length - 1)

    kept.push(
      `HERMES_HOME_GATEWAY_ID=${name}`,
      `HERMES_HOME_MEMBER_ID=${name}`,
      `HERMES_HOME_MASTER_URL=${HOME_MASTER_INCOMING_URL}`,
      '',
    )
    return kept.join('\n')
  })
}

async function clearChannelSettings(dir: string): Promise<void> {
  await safeFileStore.updateYaml(join(dir, 'config.yaml'), (cfg) => {
    for (const section of CHANNEL_SECTIONS) delete cfg[section]
    if (cfg.platforms && typeof cfg.platforms === 'object') {
      for (const section of CHANNEL_SECTIONS) delete cfg.platforms[section]
      if (Object.keys(cfg.platforms).length === 0) delete cfg.platforms
    }
    return cfg
  })
  await safeFileStore.updateText(join(dir, '.env'), (current) => {
    const blocked = new Set(CHANNEL_ENV_KEYS)
    return current
      .split(/\r?\n/)
      .filter(line => {
        const match = line.match(/^\s*([A-Z0-9_]+)\s*=/)
        return !match || !blocked.has(match[1])
      })
      .join('\n')
      .replace(/\n{3,}/g, '\n\n')
      .replace(/\n+$/, '') + '\n'
  })
}

async function enableRelayPlugin(dir: string): Promise<void> {
  await execFileAsync(getHermesBin(), ['plugins', 'enable', 'home-slave-relay'], {
    timeout: 30000,
    windowsHide: true,
    env: {
      ...process.env,
      HERMES_HOME: dir,
    },
  })
}

async function addSlaveToHomeConfig(name: string, dir: string): Promise<void> {
  if (!existsSync(HOME_CONFIG_PATH)) return
  await safeFileStore.updateYaml(HOME_CONFIG_PATH, (cfg) => {
    if (!cfg.slaves) cfg.slaves = {}
    cfg.slaves[name] = {
      member_id: name,
      member_name: '',
      hermes_home: dir,
      allowed_user_ids: ['*'],
    }
    return cfg
  })
}

async function attachHomeMemberNames(gateways: any[]): Promise<any[]> {
  if (!existsSync(HOME_CONFIG_PATH)) return gateways
  try {
    const cfg = await safeFileStore.readYaml(HOME_CONFIG_PATH)
    const slaves = cfg.slaves || {}
    return gateways.map((gateway) => {
      const slave = slaves[gateway.profile] || {}
      const memberName = String(slave.member_name || '').trim()
      return {
        ...gateway,
        home_slave: Boolean(slaves[gateway.profile]),
        member_name: memberName,
        display_name: memberName || gateway.profile,
      }
    })
  } catch {
    return gateways
  }
}

async function setHomeMemberName(name: string, memberName: string): Promise<void> {
  if (!existsSync(HOME_CONFIG_PATH)) throw new Error('Home config not found')
  let found = false
  await safeFileStore.updateYaml(HOME_CONFIG_PATH, (cfg) => {
    if (!cfg.slaves) cfg.slaves = {}
    if (!cfg.slaves[name]) return cfg
    cfg.slaves[name] = {
      ...cfg.slaves[name],
      member_name: memberName,
    }
    found = true
    return cfg
  })
  if (!found) throw new Error(`Gateway "${name}" is not registered as a home slave.`)
}

export async function list(ctx: any) {
  const mgr = getGatewayManagerInstance()
  if (!mgr) { ctx.status = 503; ctx.body = { error: 'GatewayManager not initialized' }; return }
  const gateways = await attachHomeMemberNames(await mgr.listAll())
  ctx.body = { gateways }
}

export async function updateMemberName(ctx: any) {
  const name = normalizeProfileName(ctx.params.name)
  const memberName = String((ctx.request.body as { member_name?: string } | undefined)?.member_name || '').trim()
  if (!PROFILE_NAME_RE.test(name)) {
    ctx.status = 400
    ctx.body = { error: 'Invalid gateway name' }
    return
  }
  if (memberName.length > 40) {
    ctx.status = 400
    ctx.body = { error: 'Member name is too long' }
    return
  }
  const mgr = getGatewayManagerInstance()
  if (!mgr) { ctx.status = 503; ctx.body = { error: 'GatewayManager not initialized' }; return }
  try {
    await setHomeMemberName(name, memberName)
    const gateway = (await attachHomeMemberNames([await mgr.detectStatus(name)]))[0]
    ctx.body = { success: true, gateway }
  } catch (err: any) {
    ctx.status = err.message?.includes('not registered') ? 404 : 500
    ctx.body = { error: err.message }
  }
}

export async function create(ctx: any) {
  const mgr = getGatewayManagerInstance()
  if (!mgr) { ctx.status = 503; ctx.body = { error: 'GatewayManager not initialized' }; return }

  try {
    const existingProfiles = await mgr.listProfiles()
    const requestedName = normalizeProfileName((ctx.request.body as { name?: string } | undefined)?.name)
    const name = requestedName || (await suggestProfileName(existingProfiles))
    if (!PROFILE_NAME_RE.test(name)) {
      ctx.status = 400
      ctx.body = { error: 'Gateway name must be 2-32 lowercase letters, numbers, underscores, or hyphens.' }
      return
    }
    if (name === 'default' || existingProfiles.includes(name)) {
      ctx.status = 409
      ctx.body = { error: `Gateway profile "${name}" already exists.` }
      return
    }

    const root = detectHermesRootHome()
    const dir = profileDir(root, name)
    const port = await mgr.allocateNextPort()
    const { stdout, stderr } = await execFileAsync(getHermesBin(), [
      'profile',
      'create',
      name,
      '--clone',
      '--clone-from',
      HOME_MASTER_PROFILE,
      '--no-alias',
    ], {
      timeout: 30000,
      windowsHide: true,
      env: createCliEnv(root),
    })

    await clearChannelSettings(dir)
    await mgr.configureProfilePort(name, port)
    await installRelayPlugin(dir)
    await configureRelayEnv(dir, name)
    await enableRelayPlugin(dir)
    await addSlaveToHomeConfig(name, dir)

    const gateway = (await attachHomeMemberNames([await mgr.start(name)]))[0]
    ctx.body = {
      success: true,
      name,
      port,
      gateway,
      message: `${stdout}${stderr}`.trim(),
    }
  } catch (err: any) {
    ctx.status = 500
    ctx.body = { error: err.message }
  }
}

export async function start(ctx: any) {
  const mgr = getGatewayManagerInstance()
  if (!mgr) { ctx.status = 503; ctx.body = { error: 'GatewayManager not initialized' }; return }
  try {
    const status = (await attachHomeMemberNames([await mgr.start(ctx.params.name)]))[0]
    ctx.body = { success: true, gateway: status }
  } catch (err: any) { ctx.status = 500; ctx.body = { error: err.message } }
}

export async function stop(ctx: any) {
  const mgr = getGatewayManagerInstance()
  if (!mgr) { ctx.status = 503; ctx.body = { error: 'GatewayManager not initialized' }; return }
  try {
    await mgr.stop(ctx.params.name)
    ctx.body = { success: true }
  } catch (err: any) { ctx.status = 500; ctx.body = { error: err.message } }
}

export async function health(ctx: any) {
  const mgr = getGatewayManagerInstance()
  if (!mgr) { ctx.status = 503; ctx.body = { error: 'GatewayManager not initialized' }; return }
  const status = (await attachHomeMemberNames([await mgr.detectStatus(ctx.params.name)]))[0]
  ctx.body = { gateway: status }
}
