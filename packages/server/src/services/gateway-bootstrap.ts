let gatewayManager: any = null

export function getGatewayManagerInstance(): any {
  return gatewayManager
}

export async function initGatewayManager(): Promise<void> {
  const { GatewayManager } = await import('./hermes/gateway-manager')
  const { ensureManagedProfileActive } = await import('./hermes/hermes-profile')
  const activeProfile = ensureManagedProfileActive()
  gatewayManager = new GatewayManager(activeProfile)

  await gatewayManager.detectAllOnStartup()
  await gatewayManager.startAll()
}
