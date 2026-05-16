import axios from 'axios'
import { chmod } from 'fs/promises'
import { existsSync } from 'fs'
import { join } from 'path'
import { getGatewayManagerInstance } from '../../services/gateway-bootstrap'
import { getActiveProfileName, getHermesBaseDir } from '../../services/hermes/hermes-profile'
import { safeFileStore } from '../../services/safe-file-store'

const ILINK_BASE = 'https://ilinkai.weixin.qq.com'

function normalizeProfileName(name?: string): string {
  return String(name || '').trim().toLowerCase()
}

function getRequestProfile(ctx: any): string {
  const fromQuery = typeof ctx.query?.profile === 'string' ? ctx.query.profile : ''
  const fromBody = typeof ctx.request?.body?.profile === 'string' ? ctx.request.body.profile : ''
  return normalizeProfileName(fromBody || fromQuery || getActiveProfileName())
}

function resolveProfileDir(profile: string): string {
  const base = getHermesBaseDir()
  if (!profile || profile === 'default') return base
  const dir = join(base, 'profiles', profile)
  if (!existsSync(dir)) throw new Error(`Profile "${profile}" not found`)
  return dir
}

function envPath(ctx: any): string {
  return join(resolveProfileDir(getRequestProfile(ctx)), '.env')
}

async function restartProfileGateway(profile: string): Promise<void> {
  const mgr = getGatewayManagerInstance()
  if (!mgr) return
  await mgr.stop(profile)
  await mgr.start(profile)
}

export async function getQrcode(ctx: any) {
  try {
    const res = await axios.get(`${ILINK_BASE}/ilink/bot/get_bot_qrcode`, { params: { bot_type: 3 }, timeout: 15000 })
    const data = res.data
    if (!data || !data.qrcode) { ctx.status = 500; ctx.body = { error: 'Failed to get QR code' }; return }
    ctx.body = { qrcode: data.qrcode, qrcode_url: data.qrcode_img_content }
  } catch (err: any) {
    ctx.status = 500; ctx.body = { error: err.message || 'Failed to connect to iLink API' }
  }
}

export async function pollStatus(ctx: any) {
  const qrcode = ctx.query.qrcode as string
  if (!qrcode) { ctx.status = 400; ctx.body = { error: 'Missing qrcode parameter' }; return }
  try {
    const res = await axios.get(`${ILINK_BASE}/ilink/bot/get_qrcode_status`, { params: { qrcode }, timeout: 35000 })
    const data = res.data
    const status = data?.status || 'wait'
    if (status === 'confirmed') {
      ctx.body = { status: 'confirmed', account_id: data.ilink_bot_id, token: data.bot_token, base_url: data.baseurl }
    } else {
      ctx.body = { status }
    }
  } catch (err: any) {
    ctx.status = 500; ctx.body = { error: err.message || 'Failed to poll QR status' }
  }
}

export async function save(ctx: any) {
  const { account_id, token, base_url } = ctx.request.body as { account_id: string; token: string; base_url?: string }
  if (!account_id || !token) { ctx.status = 400; ctx.body = { error: 'Missing account_id or token' }; return }
  try {
    const profile = getRequestProfile(ctx)
    const entries: Record<string, string> = { WEIXIN_ACCOUNT_ID: account_id, WEIXIN_TOKEN: token }
    if (base_url) entries.WEIXIN_BASE_URL = base_url
    const ep = envPath(ctx)
    await safeFileStore.updateText(ep, (raw) => {
      const lines = raw.split('\n')
      const existingKeys = new Set<string>()
      const result: string[] = []
      for (const line of lines) {
        const trimmed = line.trim()
        if (trimmed.startsWith('#')) { result.push(line); continue }
        const eqIdx = trimmed.indexOf('=')
        if (eqIdx !== -1) {
          const key = trimmed.slice(0, eqIdx).trim()
          if (key in entries) { result.push(`${key}=${entries[key]}`); existingKeys.add(key); continue }
        }
        result.push(line)
      }
      for (const [key, val] of Object.entries(entries)) { if (!existingKeys.has(key)) { result.push(`${key}=${val}`) } }
      return result.join('\n').replace(/\n{3,}/g, '\n\n').replace(/\n+$/, '') + '\n'
    })
    try { await chmod(ep, 0o600) } catch { }
    await restartProfileGateway(profile)
    ctx.body = { success: true }
  } catch (err: any) {
    ctx.status = 500; ctx.body = { error: err.message }
  }
}
