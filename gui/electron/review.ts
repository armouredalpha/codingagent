import fs from 'node:fs'
import path from 'node:path'
import { REPO_ROOT } from './paths'

const OBS_PATH = path.join(REPO_ROOT, 'calibration', 'observations.jsonl')
const SETS_DIR = path.join(REPO_ROOT, 'calibration', 'eval-sets')

function ensureSetsDir() {
  if (!fs.existsSync(SETS_DIR)) fs.mkdirSync(SETS_DIR, { recursive: true })
}

function readObservations(): { qid: string; approved: boolean; reason: string; reason_category?: string; source: string; ts: string }[] {
  if (!fs.existsSync(OBS_PATH)) return []
  return fs.readFileSync(OBS_PATH, 'utf-8')
    .split('\n')
    .filter(Boolean)
    .map((line) => { try { return JSON.parse(line) } catch { return null } })
    .filter(Boolean)
}

export const handleReview = {
  record(qid: string, approved: boolean, reason: string, reasonCategory?: string): void {
    const line = JSON.stringify({
      qid,
      approved,
      reason,
      reason_category: reasonCategory || undefined,
      source: 'instructor',
      ts: new Date().toISOString(),
    })
    fs.mkdirSync(path.dirname(OBS_PATH), { recursive: true })
    fs.appendFileSync(OBS_PATH, line + '\n', 'utf-8')
  },

  getInsights(): { category: string; count: number }[] {
    const obs = readObservations()
    const rejected = obs.filter((o) => !o.approved && o.reason_category)
    const counts: Record<string, number> = {}
    for (const o of rejected) {
      const cat = o.reason_category!
      counts[cat] = (counts[cat] ?? 0) + 1
    }
    return Object.entries(counts)
      .map(([category, count]) => ({ category, count }))
      .sort((a, b) => b.count - a.count)
  },

  listSets(): { name: string; created_at: string; count: number; annotated: number }[] {
    ensureSetsDir()
    return fs.readdirSync(SETS_DIR)
      .filter((f) => f.endsWith('.json'))
      .map((f) => {
        try {
          const s = JSON.parse(fs.readFileSync(path.join(SETS_DIR, f), 'utf-8'))
          return {
            name: s.name,
            created_at: s.created_at,
            count: s.questions?.length ?? 0,
            annotated: (s.questions ?? []).filter((q: { annotation?: { approved: unknown } }) => q.annotation?.approved !== null).length,
          }
        } catch { return null }
      })
      .filter(Boolean) as { name: string; created_at: string; count: number; annotated: number }[]
  },

  loadSet(name: string): unknown {
    const file = path.join(SETS_DIR, `${name}.json`)
    if (!fs.existsSync(file)) return null
    try { return JSON.parse(fs.readFileSync(file, 'utf-8')) } catch { return null }
  },

  saveSet(set: { name: string }): void {
    ensureSetsDir()
    fs.writeFileSync(path.join(SETS_DIR, `${set.name}.json`), JSON.stringify(set, null, 2), 'utf-8')
  },

  deleteSet(name: string): void {
    const file = path.join(SETS_DIR, `${name}.json`)
    if (fs.existsSync(file)) fs.unlinkSync(file)
  },
}
