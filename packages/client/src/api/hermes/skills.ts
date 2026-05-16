import { request } from '../client'

export type SkillSource = 'builtin' | 'hub' | 'local'

export interface SkillInfo {
  name: string
  description: string
  enabled?: boolean
  source?: SkillSource
  modified?: boolean
  patchCount?: number
  useCount?: number
  viewCount?: number
  pinned?: boolean
}

export interface SkillCategory {
  name: string
  description: string
  skills: SkillInfo[]
}

export interface SkillListResponse {
  categories: SkillCategory[]
  archived: SkillInfo[]
}

export interface SkillFileEntry {
  path: string
  name: string
  isDir: boolean
}

export interface MemoryData {
  memory: string
  user: string
  soul: string
  memory_mtime: number | null
  user_mtime: number | null
  soul_mtime: number | null
}

export interface FamilyLogEntry {
  id: number
  created_at: number
  occurred_at: number
  gateway_id: string
  member_id: string
  source: string
  title: string
  content: string
  tags: string
  importance: number
}

export interface SkillsData {
  categories: SkillCategory[]
  archived: SkillInfo[]
}

export interface SkillUsageRow {
  skill: string
  view_count: number
  manage_count: number
  total_count: number
  percentage: number
  last_used_at: number | null
}

export interface SkillUsageDailySkillRow {
  skill: string
  view_count: number
  manage_count: number
  total_count: number
}

export interface SkillUsageDailyRow {
  date: string
  view_count: number
  manage_count: number
  total_count: number
  skills: SkillUsageDailySkillRow[]
}

export interface SkillUsageStats {
  period_days: number
  summary: {
    total_skill_loads: number
    total_skill_edits: number
    total_skill_actions: number
    distinct_skills_used: number
  }
  by_day: SkillUsageDailyRow[]
  top_skills: SkillUsageRow[]
}

export async function fetchSkills(): Promise<SkillsData> {
  const res = await request<SkillListResponse>('/api/hermes/skills')
  return { categories: res.categories, archived: res.archived ?? [] }
}

export async function fetchSkillUsageStats(days = 7): Promise<SkillUsageStats> {
  const params = new URLSearchParams({ days: String(days) })
  return request<SkillUsageStats>(`/api/hermes/skills/usage/stats?${params}`)
}

export async function fetchSkillContent(skillPath: string): Promise<string> {
  const res = await request<{ content: string }>(`/api/hermes/skills/${skillPath}`)
  return res.content
}

export async function fetchSkillFiles(category: string, skill: string): Promise<SkillFileEntry[]> {
  const res = await request<{ files: SkillFileEntry[] }>(`/api/hermes/skills/${category}/${skill}/files`)
  return res.files
}

export async function fetchMemory(): Promise<MemoryData> {
  return request<MemoryData>('/api/hermes/memory')
}

export async function saveMemory(section: 'memory' | 'user' | 'soul', content: string): Promise<void> {
  await request('/api/hermes/memory', {
    method: 'POST',
    body: JSON.stringify({ section, content }),
  })
}

export async function fetchFamilyLogs(q = '', limit = 80, minImportance = 1): Promise<FamilyLogEntry[]> {
  const params = new URLSearchParams({ limit: String(limit) })
  if (q.trim()) params.set('q', q.trim())
  if (minImportance > 1) params.set('min_importance', String(minImportance))
  const res = await request<{ logs: FamilyLogEntry[] }>(`/api/hermes/family-logs?${params}`)
  return res.logs
}

export async function addFamilyLog(data: {
  occurred_at?: number
  gateway_id?: string
  member_id?: string
  source?: string
  title: string
  content: string
  tags?: string
  importance?: number
}): Promise<void> {
  await request('/api/hermes/family-logs', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateFamilyLog(id: number, data: {
  occurred_at?: number
  gateway_id?: string
  member_id?: string
  source?: string
  title: string
  content: string
  tags?: string
  importance?: number
}): Promise<void> {
  await request(`/api/hermes/family-logs/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteFamilyLog(id: number): Promise<void> {
  await request(`/api/hermes/family-logs/${id}`, { method: 'DELETE' })
}

export async function toggleSkill(name: string, enabled: boolean): Promise<void> {
  await request('/api/hermes/skills/toggle', {
    method: 'PUT',
    body: JSON.stringify({ name, enabled }),
  })
}

export async function pinSkillApi(name: string, pinned: boolean): Promise<void> {
  await request('/api/hermes/skills/pin', {
    method: 'PUT',
    body: JSON.stringify({ name, pinned }),
  })
}
