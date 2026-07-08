import fs from 'node:fs'
import path from 'node:path'
import initSqlJs, { type Database, type SqlJsStatic } from 'sql.js'
import { DB_PATH } from './paths'

let SQL: SqlJsStatic | null = null
let db: Database | null = null

async function ensure(): Promise<Database | null> {
  if (!SQL) {
    SQL = await initSqlJs({
      locateFile: (file) => path.join(path.dirname(require.resolve('sql.js')), file),
    })
  }
  if (!fs.existsSync(DB_PATH)) return null
  if (!db) db = new SQL.Database(fs.readFileSync(DB_PATH))
  return db
}

export function reload(): void {
  if (db) { db.close(); db = null }
}

function rows(d: Database, sql: string): Record<string, unknown>[] {
  const res = d.exec(sql)
  if (!res.length) return []
  const { columns, values } = res[0]
  return values.map((row) => Object.fromEntries(row.map((v, i) => [columns[i], v])))
}

function scalar(d: Database, sql: string): number {
  const r = d.exec(sql)
  return r.length && r[0].values.length ? Number(r[0].values[0][0] ?? 0) : 0
}

export async function rowCounts(): Promise<{ runs: number; events: number }> {
  const d = await ensure()
  if (!d) return { runs: 0, events: 0 }
  const count = (t: string) => {
    try { return scalar(d, `SELECT COUNT(*) FROM ${t}`) } catch { return 0 }
  }
  return { runs: count('runs'), events: count('events') }
}

export async function lastRun(): Promise<Record<string, unknown> | null> {
  const d = await ensure()
  if (!d) return null
  const r = rows(d, `SELECT * FROM runs ORDER BY started_at DESC LIMIT 1`)
  return r[0] ?? null
}

export async function recentRuns(limit = 15): Promise<Record<string, unknown>[]> {
  const d = await ensure()
  if (!d) return []
  const n = Math.max(1, Math.floor(Number(limit) || 15))
  return rows(d, `SELECT * FROM runs ORDER BY started_at DESC LIMIT ${n}`)
}

export async function dashboardKpis(): Promise<{
  totalRuns: number; totalQuestions: number; approved: number; rejected: number
  approvalRate: number; avgCostPerRun: number
}> {
  const d = await ensure()
  if (!d) return { totalRuns: 0, totalQuestions: 0, approved: 0, rejected: 0, approvalRate: 0, avgCostPerRun: 0 }
  const totalRuns = scalar(d, 'SELECT COUNT(*) FROM runs')
  const totalQuestions = scalar(d, 'SELECT COALESCE(SUM(n_questions),0) FROM runs')
  const approved = scalar(d, 'SELECT COALESCE(SUM(n_approved),0) FROM runs')
  const rejected = totalQuestions - approved
  let avgCostPerRun = 0
  try {
    avgCostPerRun = scalar(d, 'SELECT COALESCE(AVG(cost_usd),0) FROM runs WHERE cost_usd IS NOT NULL AND cost_usd > 0')
  } catch { /* cost_usd column not yet added */ }
  return { totalRuns, totalQuestions, approved, rejected,
    approvalRate: totalQuestions ? approved / totalQuestions : 0,
    avgCostPerRun }
}

export async function agentEventHeatmap(): Promise<{ agent: string; status: string; count: number }[]> {
  const d = await ensure()
  if (!d) return []
  try {
    return rows(d, `SELECT agent, status, COUNT(*) AS count FROM events GROUP BY agent, status`)
      .map((r) => ({ agent: String(r.agent ?? ''), status: String(r.status ?? ''), count: Number(r.count ?? 0) }))
  } catch {
    return []
  }
}

export async function runEvents(run_id: string): Promise<Record<string, unknown>[]> {
  const d = await ensure()
  if (!d) return []
  try {
    const stmt = d.prepare('SELECT * FROM events WHERE run_id = ? ORDER BY ts')
    stmt.bind([run_id])
    const out: Record<string, unknown>[] = []
    while (stmt.step()) out.push(stmt.getAsObject())
    stmt.free()
    return out
  } catch {
    return []
  }
}

export async function questionTrace(run_id: string): Promise<Record<string, unknown>[]> {
  const d = await ensure()
  if (!d) return []
  try {
    const stmt = d.prepare(
      'SELECT question_id, agent, decision, reason, ts FROM question_traces WHERE run_id = ? ORDER BY ts'
    )
    stmt.bind([run_id])
    const out: Record<string, unknown>[] = []
    while (stmt.step()) out.push(stmt.getAsObject())
    stmt.free()
    return out
  } catch {
    // Table may not exist in older DBs — return empty gracefully
    return []
  }
}
