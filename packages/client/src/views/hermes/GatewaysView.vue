<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NButton, NForm, NFormItem, NInput, NModal, NSpin, NTag, useMessage } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import { useGatewayStore } from '@/stores/hermes/gateways'

const { t } = useI18n()
const message = useMessage()
const gatewayStore = useGatewayStore()

const createModalVisible = ref(false)
const newGatewayName = ref('')
const memberNameModalVisible = ref(false)
const editingGatewayName = ref('')
const editingMemberName = ref('')

const suggestedGatewayName = computed(() => {
  let max = 2
  for (const gateway of gatewayStore.gateways) {
    const match = gateway.profile.match(/^wechat(\d+)$/)
    if (match) max = Math.max(max, Number(match[1]))
  }
  return `wechat${max + 1}`
})

onMounted(() => {
  gatewayStore.fetchStatus()
})

function openCreateModal() {
  newGatewayName.value = suggestedGatewayName.value
  createModalVisible.value = true
}

function openMemberNameModal(profile: string, memberName?: string) {
  editingGatewayName.value = profile
  editingMemberName.value = memberName || ''
  memberNameModalVisible.value = true
}

async function handleCreateGateway() {
  const name = newGatewayName.value.trim()
  try {
    const result = await gatewayStore.create(name || undefined)
    message.success(`已创建网关 ${result.name}，端口 ${result.port}`)
    createModalVisible.value = false
    await gatewayStore.fetchStatus()
  } catch (err: any) {
    message.error(err.message)
  }
}

async function handleUpdateMemberName() {
  if (!editingGatewayName.value) return
  try {
    await gatewayStore.updateMemberName(editingGatewayName.value, editingMemberName.value.trim())
    message.success('已更新显示名')
    memberNameModalVisible.value = false
  } catch (err: any) {
    message.error(err.message)
  }
}

async function handleToggle(name: string, running: boolean) {
  try {
    if (running) {
      await gatewayStore.stop(name)
      message.success(`${t('gateways.stopped')}: ${name}`)
    } else {
      await gatewayStore.start(name)
      message.success(`${t('gateways.started')}: ${name}`)
    }
  } catch (err: any) {
    message.error(err.message)
  }
}
</script>

<template>
  <div class="gateways-view">
    <header class="page-header">
      <h2 class="header-title">{{ t('gateways.title') }}</h2>
      <NButton type="primary" :loading="gatewayStore.loading" @click="openCreateModal">新建网关</NButton>
    </header>

    <div class="gateways-content">
      <NSpin :show="gatewayStore.loading" size="large">
        <div v-if="gatewayStore.gateways.length === 0" class="empty-state">{{ t('common.noData') }}</div>

        <div v-else class="gateway-list">
          <div v-for="gw in gatewayStore.gateways" :key="gw.profile" class="gateway-card">
            <div class="gateway-info">
              <div class="gateway-name">
                {{ gw.display_name || gw.profile }}
                <NTag v-if="gw.role === 'master'" size="small" type="info" round>master</NTag>
              </div>
              <div class="gateway-meta">
                <span v-if="gw.display_name && gw.display_name !== gw.profile" class="meta-item">{{ gw.profile }}</span>
                <span class="meta-item">{{ gw.host }}:{{ gw.port }}</span>
                <span v-if="gw.pid" class="meta-item">PID: {{ gw.pid }}</span>
              </div>
              <div v-if="gw.diagnostics" class="gateway-diagnostics">
                <span class="diag-item">{{ gw.diagnostics.reason }}</span>
                <span class="diag-item">{{ gw.diagnostics.config_path }}</span>
              </div>
            </div>
            <div class="gateway-actions">
              <NButton v-if="gw.home_slave" size="small" tertiary round @click="openMemberNameModal(gw.profile, gw.member_name)">改名</NButton>
              <NTag :type="gw.running ? 'success' : 'default'" size="small" round>
                {{ gw.running ? t('gateways.running') : t('gateways.stopped') }}
              </NTag>
              <NButton size="small" :type="gw.running ? 'warning' : 'primary'" round @click="handleToggle(gw.profile, gw.running)">
                {{ gw.running ? t('common.stop') : t('common.start') }}
              </NButton>
            </div>
          </div>
        </div>
      </NSpin>
    </div>

    <NModal
      v-model:show="createModalVisible"
      preset="dialog"
      title="新建网关"
      positive-text="创建并启动"
      negative-text="取消"
      :positive-button-props="{ loading: gatewayStore.loading }"
      @positive-click="handleCreateGateway"
    >
      <NForm label-placement="top">
        <NFormItem label="网关名称">
          <NInput v-model:value="newGatewayName" placeholder="wechat3" />
        </NFormItem>
      </NForm>
    </NModal>

    <NModal
      v-model:show="memberNameModalVisible"
      preset="dialog"
      title="修改显示名"
      positive-text="保存"
      negative-text="取消"
      :positive-button-props="{ loading: gatewayStore.loading }"
      @positive-click="handleUpdateMemberName"
    >
      <NForm label-placement="top">
        <NFormItem label="网关">
          <NInput :value="editingGatewayName" disabled />
        </NFormItem>
        <NFormItem label="显示名">
          <NInput v-model:value="editingMemberName" placeholder="例如：妈妈、爸爸、小王" />
        </NFormItem>
      </NForm>
    </NModal>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.gateways-view {
  height: calc(100 * var(--vh));
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.gateways-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.empty-state {
  text-align: center;
  color: $text-muted;
  padding: 40px 0;
}

.gateway-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.gateway-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 20px;
  background-color: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  transition: border-color $transition-fast;

  &:hover {
    border-color: $text-muted;
  }
}

.gateway-info {
  min-width: 0;
  flex: 1;
}

.gateway-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: $text-primary;
  margin-bottom: 4px;
}

.gateway-meta,
.gateway-diagnostics {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
}

.gateway-diagnostics {
  margin-top: 6px;
}

.meta-item {
  font-size: 12px;
  color: $text-muted;
}

.diag-item {
  max-width: 100%;
  font-size: 12px;
  color: $text-muted;
  background: rgba(127, 127, 127, 0.08);
  padding: 2px 8px;
  border-radius: 999px;
  overflow-wrap: anywhere;
  line-height: 1.5;
}

.gateway-actions {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  gap: 8px;
}

@media (max-width: 640px) {
  .gateways-content {
    padding: 16px;
  }

  .gateway-card {
    align-items: stretch;
    flex-direction: column;
    padding: 16px;
  }

  .gateway-diagnostics {
    flex-direction: column;
    gap: 6px;
  }

  .diag-item {
    border-radius: $radius-sm;
  }

  .gateway-actions {
    justify-content: flex-start;
  }
}
</style>
