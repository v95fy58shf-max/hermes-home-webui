import { request } from '../client'

export interface GatewayStatus {
  profile: string
  port: number
  host: string
  url: string
  running: boolean
  role?: 'master' | 'slave'
  home_slave?: boolean
  member_name?: string
  display_name?: string
  pid?: number
  diagnostics?: {
    pid_path: string
    config_path: string
    pid_file_exists: boolean
    config_exists: boolean
    health_url: string
    health_checked_at: string
    health_ok?: boolean
    reason: string
  }
}

export async function fetchGateways(): Promise<GatewayStatus[]> {
  const res = await request<{ gateways: GatewayStatus[] }>('/api/hermes/gateways')
  return res.gateways
}

export async function createGateway(name?: string): Promise<{ gateway: GatewayStatus; name: string; port: number }> {
  const res = await request<{ success: boolean; gateway: GatewayStatus; name: string; port: number }>('/api/hermes/gateways', {
    method: 'POST',
    body: JSON.stringify({ name }),
  })
  return { gateway: res.gateway, name: res.name, port: res.port }
}

export async function updateGatewayMemberName(name: string, memberName: string): Promise<GatewayStatus> {
  const res = await request<{ success: boolean; gateway: GatewayStatus }>(`/api/hermes/gateways/${name}/member-name`, {
    method: 'PATCH',
    body: JSON.stringify({ member_name: memberName }),
  })
  return res.gateway
}

export async function startGateway(name: string): Promise<GatewayStatus> {
  const res = await request<{ success: boolean; gateway: GatewayStatus }>(`/api/hermes/gateways/${name}/start`, { method: 'POST' })
  return res.gateway
}

export async function stopGateway(name: string): Promise<void> {
  await request(`/api/hermes/gateways/${name}/stop`, { method: 'POST' })
}

export async function checkGatewayHealth(name: string): Promise<GatewayStatus> {
  const res = await request<{ gateway: GatewayStatus }>(`/api/hermes/gateways/${name}/health`)
  return res.gateway
}
