<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { NSpin, NTabPane, NTabs } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import PlatformSettings from '@/components/hermes/settings/PlatformSettings.vue'
import { useGatewayStore } from '@/stores/hermes/gateways'
import { useSettingsStore } from '@/stores/hermes/settings'

const settingsStore = useSettingsStore()
const gatewayStore = useGatewayStore()
const { t } = useI18n()
const selectedGateway = ref('')

const runningGateways = computed(() => gatewayStore.gateways.filter(gateway => gateway.running))

onMounted(() => {
  gatewayStore.fetchStatus()
})

watch(runningGateways, (gateways) => {
  if (gateways.length === 0) {
    selectedGateway.value = ''
    return
  }
  if (!gateways.some(gateway => gateway.profile === selectedGateway.value)) {
    selectedGateway.value = gateways[0].profile
  }
}, { immediate: true })

watch(selectedGateway, (profile) => {
  if (profile) settingsStore.fetchSettings(profile)
}, { immediate: true })
</script>

<template>
  <div class="channels-view">
    <header class="page-header">
      <h2 class="header-title">{{ t('sidebar.channels') }}</h2>
    </header>

    <div class="channels-content">
      <NTabs v-if="runningGateways.length > 0" v-model:value="selectedGateway" type="line" class="gateway-tabs">
        <NTabPane
          v-for="gateway in runningGateways"
          :key="gateway.profile"
          :name="gateway.profile"
          :tab="`${gateway.display_name || gateway.profile} · ${gateway.port}`"
        />
      </NTabs>

      <div v-else class="empty-state">请先在“网关”页面启动至少一个网关。</div>

      <NSpin :show="gatewayStore.loading || settingsStore.loading || settingsStore.saving" size="large" :description="t('common.loading')">
        <PlatformSettings v-if="selectedGateway && !settingsStore.loading" :key="selectedGateway" :profile="selectedGateway" />
      </NSpin>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.channels-view {
  height: calc(100 * var(--vh));
  display: flex;
  flex-direction: column;
}

.channels-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  position: relative;
}

.gateway-tabs {
  margin-bottom: 12px;
}

.empty-state {
  padding: 32px 0;
  color: $text-muted;
  text-align: center;
}
</style>
