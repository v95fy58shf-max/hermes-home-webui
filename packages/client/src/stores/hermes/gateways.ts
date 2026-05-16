import { defineStore } from 'pinia'
import { ref } from 'vue'
import { createGateway, fetchGateways, startGateway, stopGateway, updateGatewayMemberName, type GatewayStatus } from '@/api/hermes/gateways'

export const useGatewayStore = defineStore('gateways', () => {
  const gateways = ref<GatewayStatus[]>([])
  const loading = ref(false)

  async function fetchStatus() {
    loading.value = true
    try {
      const data = await fetchGateways()
      gateways.value = Array.isArray(data) ? data : Object.values(data || {})
    } finally {
      loading.value = false
    }
  }

  async function start(name: string) {
    loading.value = true
    try {
      const status = await startGateway(name)
      // Update the specific gateway in the list
      const idx = gateways.value.findIndex(g => g.profile === name)
      if (idx >= 0) {
        gateways.value[idx] = status
      } else {
        gateways.value.push(status)
      }
    } finally {
      loading.value = false
    }
  }

  async function create(name?: string) {
    loading.value = true
    try {
      const result = await createGateway(name)
      const idx = gateways.value.findIndex(g => g.profile === result.gateway.profile)
      if (idx >= 0) {
        gateways.value[idx] = result.gateway
      } else {
        gateways.value.push(result.gateway)
      }
      return result
    } finally {
      loading.value = false
    }
  }

  async function stop(name: string) {
    loading.value = true
    try {
      await stopGateway(name)
      // Update the specific gateway in the list
      const gw = gateways.value.find(g => g.profile === name)
      if (gw) {
        gw.running = false
        gw.pid = undefined
      }
    } finally {
      loading.value = false
    }
  }

  async function updateMemberName(name: string, memberName: string) {
    loading.value = true
    try {
      const status = await updateGatewayMemberName(name, memberName)
      const idx = gateways.value.findIndex(g => g.profile === name)
      if (idx >= 0) {
        gateways.value[idx] = status
      } else {
        gateways.value.push(status)
      }
      return status
    } finally {
      loading.value = false
    }
  }

  return { gateways, loading, fetchStatus, create, start, stop, updateMemberName }
})
