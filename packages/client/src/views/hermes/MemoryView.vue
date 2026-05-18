<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { NButton, NForm, NFormItem, NInput, NInputNumber, NModal, NPopconfirm, NSelect, NTabPane, NTabs, useMessage } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import MarkdownRenderer from '@/components/hermes/chat/MarkdownRenderer.vue'
import { addFamilyLog, deleteFamilyLog, fetchFamilyLogs, fetchMemory, saveMemory, updateFamilyLog, type FamilyLogEntry, type MemoryData } from '@/api/hermes/skills'
import { useGatewayStore } from '@/stores/hermes/gateways'

const { t } = useI18n()
const message = useMessage()
const gatewayStore = useGatewayStore()

const loading = ref(false)
const data = ref<MemoryData | null>(null)
const selectedGateway = ref('')
const editingSection = ref<'memory' | 'user' | 'soul' | null>(null)
const editContent = ref('')
const saving = ref(false)

const familyLogs = ref<FamilyLogEntry[]>([])
const familyLogQuery = ref('')
const familyLogMinImportance = ref(1)
const familyLogModalVisible = ref(false)
const familyLogSaving = ref(false)
const editingFamilyLogId = ref<number | null>(null)
const familyLogForm = ref({
  occurred_at: '',
  member_id: '',
  gateway_id: '',
  title: '',
  content: '',
  tags: '',
  importance: 3,
})

const importanceOptions = [
  { label: '全部重要度', value: 1 },
  { label: '重要度 2+', value: 2 },
  { label: '重要度 3+', value: 3 },
  { label: '重要度 4+', value: 4 },
  { label: '重要度 5', value: 5 },
]

const gatewayTabs = computed(() => gatewayStore.gateways)
const familyLogModalTitle = computed(() => editingFamilyLogId.value ? '编辑共享记忆' : '新增共享记忆')
const memoryEmpty = computed(() => !data.value?.memory?.trim())
const userEmpty = computed(() => !data.value?.user?.trim())
const soulEmpty = computed(() => !data.value?.soul?.trim())
const familyLogsEmpty = computed(() => familyLogs.value.length === 0)
const displayMemory = computed(() => (data.value?.memory || '').replace(/搂/g, '\n\n'))
const displayUser = computed(() => (data.value?.user || '').replace(/搂/g, '\n\n'))
const displaySoul = computed(() => (data.value?.soul || '').replace(/搂/g, '\n\n'))

onMounted(async () => {
  await gatewayStore.fetchStatus()
  if (!selectedGateway.value && gatewayStore.gateways.length > 0) {
    selectedGateway.value = gatewayStore.gateways[0].profile
  }
  await loadMemory()
})

watch(selectedGateway, () => {
  if (!selectedGateway.value) return
  editingSection.value = null
  editContent.value = ''
  loadMemory()
})

async function loadMemory() {
  loading.value = true
  try {
    const [memoryData, logs] = await Promise.all([
      fetchMemory(selectedGateway.value || undefined),
      fetchFamilyLogs(familyLogQuery.value, 80, familyLogMinImportance.value),
    ])
    data.value = memoryData
    familyLogs.value = logs
  } catch (err: any) {
    console.error('Failed to load memory:', err)
    message.error(t('memory.loadFailed'))
  } finally {
    loading.value = false
  }
}

async function loadFamilyLogs() {
  try {
    familyLogs.value = await fetchFamilyLogs(familyLogQuery.value, 80, familyLogMinImportance.value)
  } catch (err: any) {
    message.error(err.message)
  }
}

function formatDatetimeInput(ts: number): string {
  const d = new Date(ts * 1000)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function formatTime(ts: number | null): string {
  if (!ts) return ''
  return new Date(ts).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function formatFullTime(ts: number | null): string {
  if (!ts) return ''
  return new Date(ts * 1000).toLocaleString()
}

function openFamilyLogModal() {
  const now = new Date()
  now.setSeconds(0, 0)
  editingFamilyLogId.value = null
  familyLogForm.value = {
    occurred_at: formatDatetimeInput(Math.floor(now.getTime() / 1000)),
    member_id: '',
    gateway_id: '',
    title: '',
    content: '',
    tags: '',
    importance: 3,
  }
  familyLogModalVisible.value = true
}

function openEditFamilyLogModal(log: FamilyLogEntry) {
  editingFamilyLogId.value = log.id
  familyLogForm.value = {
    occurred_at: formatDatetimeInput(log.occurred_at),
    member_id: log.member_id || '',
    gateway_id: log.gateway_id || '',
    title: log.title || '',
    content: log.content || '',
    tags: log.tags || '',
    importance: log.importance || 3,
  }
  familyLogModalVisible.value = true
}

async function handleSaveFamilyLog() {
  const form = familyLogForm.value
  if (!form.title.trim() || !form.content.trim()) {
    message.error('请填写标题和内容')
    return
  }
  familyLogSaving.value = true
  try {
    const payload = {
      occurred_at: form.occurred_at ? Math.floor(new Date(form.occurred_at).getTime() / 1000) : undefined,
      member_id: form.member_id.trim(),
      gateway_id: form.gateway_id.trim(),
      source: 'manual',
      title: form.title.trim(),
      content: form.content.trim(),
      tags: form.tags.trim(),
      importance: form.importance,
    }
    if (editingFamilyLogId.value) await updateFamilyLog(editingFamilyLogId.value, payload)
    else await addFamilyLog(payload)
    familyLogModalVisible.value = false
    editingFamilyLogId.value = null
    await loadFamilyLogs()
    message.success(t('common.saved'))
  } catch (err: any) {
    message.error(err.message)
  } finally {
    familyLogSaving.value = false
  }
}

async function handleDeleteFamilyLog(id: number) {
  try {
    await deleteFamilyLog(id)
    await loadFamilyLogs()
    message.success('已删除共享记忆')
  } catch (err: any) {
    message.error(err.message)
  }
}

function startEdit(section: 'memory' | 'user' | 'soul') {
  editingSection.value = section
  editContent.value = data.value?.[section] || ''
}

function cancelEdit() {
  editingSection.value = null
  editContent.value = ''
}

async function handleSave() {
  if (!editingSection.value) return
  saving.value = true
  try {
    await saveMemory(editingSection.value, editContent.value, selectedGateway.value || undefined)
    await loadMemory()
    editingSection.value = null
    editContent.value = ''
    message.success(t('common.saved'))
  } catch (err: any) {
    message.error(`${t('common.saveFailed')}: ${err.message}`)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="memory-view">
    <header class="page-header">
      <h2 class="header-title">{{ t('memory.title') }}</h2>
      <NButton size="small" quaternary @click="loadMemory">{{ t('memory.refresh') }}</NButton>
    </header>

    <NTabs v-if="gatewayTabs.length > 0" v-model:value="selectedGateway" type="line" class="gateway-tabs">
      <NTabPane v-for="gateway in gatewayTabs" :key="gateway.profile" :name="gateway.profile" :tab="gateway.display_name || gateway.profile" />
    </NTabs>

    <div class="memory-content">
      <div v-if="loading && !data" class="memory-loading">{{ t('common.loading') }}</div>
      <div v-else class="memory-sections">
        <div class="memory-section">
          <div class="section-header">
            <div class="section-title-row">
              <span class="section-title">{{ t('memory.myNotes') }}</span>
              <span v-if="data?.memory_mtime" class="section-mtime">{{ formatTime(data.memory_mtime) }}</span>
            </div>
            <NButton v-if="editingSection !== 'memory'" size="tiny" quaternary @click="startEdit('memory')">{{ t('common.edit') }}</NButton>
          </div>
          <div v-if="editingSection !== 'memory'" class="section-body">
            <MarkdownRenderer v-if="!memoryEmpty" :content="displayMemory" />
            <p v-else class="empty-text">{{ t('memory.noNotes') }}</p>
          </div>
          <div v-else class="section-edit">
            <textarea v-model="editContent" class="edit-textarea" :placeholder="t('memory.notesPlaceholder')" spellcheck="false"></textarea>
            <div class="edit-actions">
              <NButton size="small" @click="cancelEdit">{{ t('common.cancel') }}</NButton>
              <NButton size="small" type="primary" :loading="saving" @click="handleSave">{{ t('common.save') }}</NButton>
            </div>
          </div>
        </div>

        <div class="memory-section">
          <div class="section-header">
            <div class="section-title-row">
              <span class="section-title">{{ t('memory.userProfile') }}</span>
              <span v-if="data?.user_mtime" class="section-mtime">{{ formatTime(data.user_mtime) }}</span>
            </div>
            <NButton v-if="editingSection !== 'user'" size="tiny" quaternary @click="startEdit('user')">{{ t('common.edit') }}</NButton>
          </div>
          <div v-if="editingSection !== 'user'" class="section-body">
            <MarkdownRenderer v-if="!userEmpty" :content="displayUser" />
            <p v-else class="empty-text">{{ t('memory.noProfile') }}</p>
          </div>
          <div v-else class="section-edit">
            <textarea v-model="editContent" class="edit-textarea" :placeholder="t('memory.profilePlaceholder')" spellcheck="false"></textarea>
            <div class="edit-actions">
              <NButton size="small" @click="cancelEdit">{{ t('common.cancel') }}</NButton>
              <NButton size="small" type="primary" :loading="saving" @click="handleSave">{{ t('common.save') }}</NButton>
            </div>
          </div>
        </div>

        <div class="memory-section">
          <div class="section-header">
            <div class="section-title-row">
              <span class="section-title">{{ t('memory.soul') }}</span>
              <span v-if="data?.soul_mtime" class="section-mtime">{{ formatTime(data.soul_mtime) }}</span>
            </div>
            <NButton v-if="editingSection !== 'soul'" size="tiny" quaternary @click="startEdit('soul')">{{ t('common.edit') }}</NButton>
          </div>
          <div v-if="editingSection !== 'soul'" class="section-body">
            <MarkdownRenderer v-if="!soulEmpty" :content="displaySoul" />
            <p v-else class="empty-text">{{ t('memory.noSoul') }}</p>
          </div>
          <div v-else class="section-edit">
            <textarea v-model="editContent" class="edit-textarea" :placeholder="t('memory.soulPlaceholder')" spellcheck="false"></textarea>
            <div class="edit-actions">
              <NButton size="small" @click="cancelEdit">{{ t('common.cancel') }}</NButton>
              <NButton size="small" type="primary" :loading="saving" @click="handleSave">{{ t('common.save') }}</NButton>
            </div>
          </div>
        </div>

        <div class="memory-section shared-memory-section">
          <div class="section-header">
            <div class="section-title-row">
              <span class="section-title">共享记忆</span>
              <span class="section-mtime">长期保存，按需检索</span>
            </div>
            <NButton size="tiny" quaternary @click="openFamilyLogModal">新增</NButton>
          </div>
          <div class="section-body family-log-body">
            <div class="family-log-toolbar">
              <NInput v-model:value="familyLogQuery" size="small" clearable placeholder="搜索成员、标签或内容" @keyup.enter="loadFamilyLogs" />
              <NSelect v-model:value="familyLogMinImportance" size="small" class="family-log-importance-select" :options="importanceOptions" @update:value="loadFamilyLogs" />
              <NButton size="small" @click="loadFamilyLogs">搜索</NButton>
            </div>
            <div v-if="familyLogsEmpty" class="empty-text">暂无共享记忆</div>
            <div v-else class="family-log-list">
              <article v-for="log in familyLogs" :key="log.id" class="family-log-item">
                <div class="family-log-title-row">
                  <strong>{{ log.title }}</strong>
                  <span>{{ formatFullTime(log.occurred_at) }}</span>
                </div>
                <p>{{ log.content }}</p>
                <div class="family-log-meta">
                  <span v-if="log.member_id">{{ log.member_id }}</span>
                  <span v-if="log.gateway_id">{{ log.gateway_id }}</span>
                  <span v-if="log.tags">{{ log.tags }}</span>
                  <span>重要度 {{ log.importance }}</span>
                </div>
                <div class="family-log-actions">
                  <NButton size="tiny" quaternary @click="openEditFamilyLogModal(log)">编辑</NButton>
                  <NPopconfirm @positive-click="handleDeleteFamilyLog(log.id)">
                    <template #trigger>
                      <NButton size="tiny" quaternary type="error">删除</NButton>
                    </template>
                    删除这条共享记忆？
                  </NPopconfirm>
                </div>
              </article>
            </div>
          </div>
        </div>
      </div>
    </div>

    <NModal v-model:show="familyLogModalVisible" preset="dialog" :title="familyLogModalTitle" positive-text="保存" negative-text="取消" :positive-button-props="{ loading: familyLogSaving }" @positive-click="handleSaveFamilyLog">
      <NForm label-placement="top">
        <NFormItem label="发生时间">
          <input v-model="familyLogForm.occurred_at" class="native-input" type="datetime-local" />
        </NFormItem>
        <NFormItem label="标题">
          <NInput v-model:value="familyLogForm.title" placeholder="例如：下周三复诊 / 客户下周回访 / 项目节点确认" />
        </NFormItem>
        <NFormItem label="内容">
          <NInput v-model:value="familyLogForm.content" type="textarea" placeholder="记录事实、决定、时间点、地点、涉及成员等" />
        </NFormItem>
        <NFormItem label="成员 / 网关">
          <div class="family-log-form-row">
            <NInput v-model:value="familyLogForm.member_id" placeholder="成员" />
            <NInput v-model:value="familyLogForm.gateway_id" placeholder="网关" />
          </div>
        </NFormItem>
        <NFormItem label="标签 / 重要度">
          <div class="family-log-form-row">
            <NInput v-model:value="familyLogForm.tags" placeholder="健康,日程,项目,客户,偏好" />
            <NInputNumber v-model:value="familyLogForm.importance" :min="1" :max="5" />
          </div>
        </NFormItem>
      </NForm>
    </NModal>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.memory-view {
  height: calc(100 * var(--vh));
  display: flex;
  flex-direction: column;
}

.gateway-tabs {
  flex-shrink: 0;
  padding: 0 20px;
  border-bottom: 1px solid $border-color;
}

.memory-content {
  flex: 1;
  overflow: hidden;
  padding: 20px;
  display: flex;
  flex-direction: column;
}

.memory-loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: $text-muted;
}

.memory-sections {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  flex: 1;
  min-height: 0;

  @media (max-width: $breakpoint-mobile) {
    grid-template-columns: 1fr;
  }
}

.memory-section {
  min-height: 0;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.shared-memory-section {
  grid-column: 1 / -1;
  min-height: 280px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background: $bg-secondary;
  border-bottom: 1px solid $border-color;
  flex-shrink: 0;
}

.section-title-row,
.family-log-title-row,
.family-log-meta,
.family-log-form-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: $text-primary;
}

.section-mtime,
.empty-text {
  font-size: 13px;
  color: $text-muted;
}

.section-mtime {
  font-size: 11px;
}

.section-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  min-height: 0;
}

.empty-text {
  font-style: italic;
}

.section-edit {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 12px 16px;
  min-height: 0;
}

.edit-textarea {
  flex: 1;
  width: 100%;
  min-height: 0;
  padding: 12px;
  border: 1px solid $border-color;
  border-radius: $radius-sm;
  background: $bg-input;
  color: $text-primary;
  font-family: $font-code;
  font-size: 13px;
  line-height: 1.6;
  resize: none;
  outline: none;

  &:focus {
    border-color: $accent-primary;
  }
}

.edit-actions,
.family-log-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 10px;
}

.family-log-body,
.family-log-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.family-log-toolbar {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.family-log-importance-select {
  width: 132px;
  flex-shrink: 0;
}

.family-log-item {
  padding: 10px;
  border: 1px solid $border-color;
  border-radius: $radius-sm;
  background: $bg-secondary;

  p {
    margin: 8px 0;
    color: $text-primary;
    font-size: 13px;
    line-height: 1.6;
  }
}

.family-log-title-row {
  justify-content: space-between;

  span {
    color: $text-muted;
    font-size: 11px;
    white-space: nowrap;
  }
}

.family-log-meta {
  flex-wrap: wrap;

  span {
    color: $text-muted;
    font-size: 11px;
    background: rgba(127, 127, 127, 0.08);
    border-radius: 999px;
    padding: 2px 8px;
  }
}

.family-log-form-row {
  width: 100%;
}

.native-input {
  width: 100%;
  height: 34px;
  padding: 0 12px;
  border: 1px solid $border-color;
  border-radius: $radius-sm;
  background: $bg-input;
  color: $text-primary;
  outline: none;
}
</style>
