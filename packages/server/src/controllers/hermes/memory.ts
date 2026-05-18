import { DatabaseSync } from 'node:sqlite'
import { writeFile } from 'fs/promises'
import { join } from 'path'
import { safeReadFile, safeStat, getHermesDir } from '../../services/config-helpers'

const HOME_DB_PATH = process.env.HERMES_HOME_DB || '/opt/hermes-home/home.db'

function openHomeDb(): DatabaseSync {
  const db = new DatabaseSync(HOME_DB_PATH)
  db.exec(`
    CREATE TABLE IF NOT EXISTS family_logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      created_at INTEGER NOT NULL,
      occurred_at INTEGER NOT NULL,
      gateway_id TEXT,
      member_id TEXT,
      source TEXT,
      title TEXT NOT NULL,
      content TEXT NOT NULL,
      tags TEXT,
      importance INTEGER DEFAULT 3,
      raw_json TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_family_logs_occurred_at ON family_logs(occurred_at DESC);
    CREATE INDEX IF NOT EXISTS idx_family_logs_member_id ON family_logs(member_id);
  `)
  return db
}

export async function get(ctx: any) {
  const hd = getHermesDir()
  const memoryPath = join(hd, 'memories', 'MEMORY.md')
  const userPath = join(hd, 'memories', 'USER.md')
  const soulPath = join(hd, 'SOUL.md')
  const [memory, user, soul, memoryStat, userStat, soulStat] = await Promise.all([
    safeReadFile(memoryPath), safeReadFile(userPath), safeReadFile(soulPath),
    safeStat(memoryPath), safeStat(userPath), safeStat(soulPath),
  ])
  ctx.body = {
    memory: memory || '', user: user || '', soul: soul || '',
    memory_mtime: memoryStat?.mtime || null, user_mtime: userStat?.mtime || null, soul_mtime: soulStat?.mtime || null,
  }
}

export async function save(ctx: any) {
  const { section, content } = ctx.request.body as { section: string; content: string }
  if (!section || !content) {
    ctx.status = 400
    ctx.body = { error: 'Missing section or content' }
    return
  }
  if (section !== 'memory' && section !== 'user' && section !== 'soul') {
    ctx.status = 400
    ctx.body = { error: 'Section must be "memory", "user", or "soul"' }
    return
  }
  let filePath: string
  if (section === 'soul') {
    filePath = join(getHermesDir(), 'SOUL.md')
  } else {
    const fileName = section === 'memory' ? 'MEMORY.md' : 'USER.md'
    filePath = join(getHermesDir(), 'memories', fileName)
  }
  try {
    await writeFile(filePath, content, 'utf-8')
    ctx.body = { success: true }
  } catch (err: any) {
    ctx.status = 500
    ctx.body = { error: err.message }
  }
}

export async function listFamilyLogs(ctx: any) {
  try {
    const q = String(ctx.query.q || '').trim()
    const limit = Math.min(Math.max(parseInt(String(ctx.query.limit || '80'), 10) || 80, 1), 300)
    const minImportance = Math.min(Math.max(parseInt(String(ctx.query.min_importance || '1'), 10) || 1, 1), 5)
    const db = openHomeDb()
    try {
      const clauses = ['importance >= ?']
      const params: any[] = [minImportance]
      if (q) {
        clauses.push('(title LIKE ? OR content LIKE ? OR tags LIKE ? OR member_id LIKE ? OR gateway_id LIKE ?)')
        params.push(`%${q}%`, `%${q}%`, `%${q}%`, `%${q}%`, `%${q}%`)
      }
      params.push(limit)
      const rows = db.prepare(`
        SELECT * FROM family_logs
        WHERE ${clauses.join(' AND ')}
        ORDER BY occurred_at DESC, id DESC
        LIMIT ?
      `).all(...params)
      ctx.body = { logs: rows }
    } finally {
      db.close()
    }
  } catch (err: any) {
    ctx.status = 500
    ctx.body = { error: err.message }
  }
}

export async function addFamilyLog(ctx: any) {
  const body = ctx.request.body as {
    occurred_at?: number
    member_id?: string
    gateway_id?: string
    source?: string
    title?: string
    content?: string
    tags?: string
    importance?: number
  }
  const title = String(body.title || '').trim()
  const content = String(body.content || '').trim()
  if (!title || !content) {
    ctx.status = 400
    ctx.body = { error: 'Missing title or content' }
    return
  }
  try {
    const now = Math.floor(Date.now() / 1000)
    const occurredAt = Number.isFinite(body.occurred_at) && body.occurred_at ? Math.floor(Number(body.occurred_at)) : now
    const importance = Math.min(Math.max(parseInt(String(body.importance || '3'), 10) || 3, 1), 5)
    const db = openHomeDb()
    try {
      const result = db.prepare(`
        INSERT INTO family_logs (
          created_at, occurred_at, gateway_id, member_id, source, title, content, tags, importance, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `).run(
        now,
        occurredAt,
        body.gateway_id || '',
        body.member_id || '',
        body.source || 'manual',
        title,
        content,
        body.tags || '',
        importance,
        JSON.stringify({ manual: true }),
      )
      ctx.body = { success: true, id: result.lastInsertRowid }
    } finally {
      db.close()
    }
  } catch (err: any) {
    ctx.status = 500
    ctx.body = { error: err.message }
  }
}

export async function updateFamilyLog(ctx: any) {
  const id = parseInt(String(ctx.params.id || ''), 10)
  if (!Number.isFinite(id) || id <= 0) {
    ctx.status = 400
    ctx.body = { error: 'Invalid family log id' }
    return
  }
  const body = ctx.request.body as {
    occurred_at?: number
    member_id?: string
    gateway_id?: string
    source?: string
    title?: string
    content?: string
    tags?: string
    importance?: number
  }
  const title = String(body.title || '').trim()
  const content = String(body.content || '').trim()
  if (!title || !content) {
    ctx.status = 400
    ctx.body = { error: 'Missing title or content' }
    return
  }
  try {
    const now = Math.floor(Date.now() / 1000)
    const occurredAt = Number.isFinite(body.occurred_at) && body.occurred_at ? Math.floor(Number(body.occurred_at)) : now
    const importance = Math.min(Math.max(parseInt(String(body.importance || '3'), 10) || 3, 1), 5)
    const db = openHomeDb()
    try {
      const result = db.prepare(`
        UPDATE family_logs
        SET occurred_at = ?, gateway_id = ?, member_id = ?, source = ?, title = ?, content = ?, tags = ?, importance = ?
        WHERE id = ?
      `).run(
        occurredAt,
        body.gateway_id || '',
        body.member_id || '',
        body.source || 'manual',
        title,
        content,
        body.tags || '',
        importance,
        id,
      )
      if (result.changes === 0) {
        ctx.status = 404
        ctx.body = { error: 'Family log not found' }
        return
      }
      ctx.body = { success: true }
    } finally {
      db.close()
    }
  } catch (err: any) {
    ctx.status = 500
    ctx.body = { error: err.message }
  }
}

export async function deleteFamilyLog(ctx: any) {
  const id = parseInt(String(ctx.params.id || ''), 10)
  if (!Number.isFinite(id) || id <= 0) {
    ctx.status = 400
    ctx.body = { error: 'Invalid family log id' }
    return
  }
  try {
    const db = openHomeDb()
    try {
      const result = db.prepare('DELETE FROM family_logs WHERE id = ?').run(id)
      if (result.changes === 0) {
        ctx.status = 404
        ctx.body = { error: 'Family log not found' }
        return
      }
      ctx.body = { success: true }
    } finally {
      db.close()
    }
  } catch (err: any) {
    ctx.status = 500
    ctx.body = { error: err.message }
  }
}
