import { join } from 'path'
import { readFileSync, existsSync, writeFileSync } from 'fs'
import { detectHermesRootHome } from './hermes-path'

export const HOME_MASTER_PROFILE = process.env.HERMES_HOME_MASTER_PROFILE || 'home-master'
export const HOME_MASTER_DISPLAY_NAME = 'master'

export function getHermesBaseDir(): string {
  return detectHermesRootHome()
}

export function profileExists(name: string): boolean {
  if (!name || name === 'default') return existsSync(join(getHermesBaseDir(), 'config.yaml'))
  return existsSync(join(getHermesBaseDir(), 'profiles', name))
}

export function getManagedProfileName(): string {
  return profileExists(HOME_MASTER_PROFILE) ? HOME_MASTER_PROFILE : 'default'
}

export function getProfileDisplayName(name: string): string {
  return name === HOME_MASTER_PROFILE ? HOME_MASTER_DISPLAY_NAME : name
}

export function ensureManagedProfileActive(): string {
  const managed = getManagedProfileName()
  if (managed === 'default') return managed
  const activeFile = join(getHermesBaseDir(), 'active_profile')
  try {
    const current = readFileSync(activeFile, 'utf-8').trim()
    if (current === managed) return managed
  } catch {}
  try {
    writeFileSync(activeFile, `${managed}\n`, 'utf-8')
  } catch {}
  return managed
}

/**
 * Get the active profile's home directory.
 * default → ~/.hermes/
 * other   → ~/.hermes/profiles/{name}/
 */
export function getActiveProfileDir(): string {
  const hermesBase = getHermesBaseDir()
  const managed = getManagedProfileName()
  if (managed !== 'default') return join(hermesBase, 'profiles', managed)
  const activeFile = join(hermesBase, 'active_profile')
  try {
    const name = readFileSync(activeFile, 'utf-8').trim()
    if (name && name !== 'default') {
      const dir = join(hermesBase, 'profiles', name)
      if (existsSync(dir)) return dir
    }
  } catch { }
  return hermesBase
}

/**
 * Get the active profile's config.yaml path.
 */
export function getActiveConfigPath(): string {
  return join(getActiveProfileDir(), 'config.yaml')
}

/**
 * Get the active profile's auth.json path.
 */
export function getActiveAuthPath(): string {
  return join(getActiveProfileDir(), 'auth.json')
}

/**
 * Get the active profile's .env path.
 */
export function getActiveEnvPath(): string {
  return join(getActiveProfileDir(), '.env')
}

/**
 * Get the active profile name.
 */
export function getActiveProfileName(): string {
  const managed = getManagedProfileName()
  if (managed !== 'default') return managed
  const activeFile = join(getHermesBaseDir(), 'active_profile')
  try {
    const name = readFileSync(activeFile, 'utf-8').trim()
    return name || 'default'
  } catch {
    return 'default'
  }
}

/**
 * Get profile directory by name.
 * default → ~/.hermes/
 * other   → ~/.hermes/profiles/{name}/
 */
export function getProfileDir(name: string): string {
  const hermesBase = getHermesBaseDir()
  if (!name || name === 'default') return hermesBase
  const dir = join(hermesBase, 'profiles', name)
  return existsSync(dir) ? dir : hermesBase
}
