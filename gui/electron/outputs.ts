import fs from 'node:fs'
import path from 'node:path'
import YAML from 'yaml'
import { OUTPUTS_DIR } from './paths'

function readJson(file: string): Record<string, unknown> | null {
  try { return JSON.parse(fs.readFileSync(file, 'utf-8')) } catch { return null }
}
function readYaml(file: string): Record<string, unknown> | null {
  try { return YAML.parse(fs.readFileSync(file, 'utf-8')) ?? null } catch { return null }
}

export function readUsageHistory(): { run_id: string; [key: string]: unknown }[] {
  const file = path.join(OUTPUTS_DIR, 'usage_history.jsonl')
  if (!fs.existsSync(file)) return []
  return fs.readFileSync(file, 'utf-8')
    .split('\n')
    .filter(Boolean)
    .map((line) => { try { return JSON.parse(line) } catch { return null } })
    .filter(Boolean)
    .reverse() // newest first
}

// Leaf-content directory names: never contain nested run folders, so recursion stops here.
const LEAF_DIRS = new Set(['questions', 'rejected', 'reports', 'boilerplate', 'evaluation', 'solution'])

function isRunDir(full: string, entries: fs.Dirent[]): boolean {
  if (fs.existsSync(path.join(full, 'run_metadata.json'))) return true
  const hasQuestionsDir = entries.some((e) => e.isDirectory() && (e.name === 'questions' || e.name === 'rejected'))
  if (!hasQuestionsDir) return false
  // Older/manual runs: no run_metadata.json, but package.json identifies a run.
  if (fs.existsSync(path.join(full, 'package.json'))) return true
  // Manually recovered/imported dumps: no metadata file at all — a non-empty
  // questions/rejected dir is enough to treat this as a run.
  return countQuestions(full, 'questions') + countQuestions(full, 'rejected') > 0
}

function findRunDirs(root: string, depth = 0, maxDepth = 6): string[] {
  if (depth > maxDepth) return []
  let entries: fs.Dirent[]
  try { entries = fs.readdirSync(root, { withFileTypes: true }) } catch { return [] }
  const found: string[] = []
  if (isRunDir(root, entries)) found.push(root)
  for (const e of entries) {
    if (!e.isDirectory() || LEAF_DIRS.has(e.name)) continue
    found.push(...findRunDirs(path.join(root, e.name), depth + 1, maxDepth))
  }
  return found
}

function isQuestionFile(qPath: string, stat: fs.Stats): boolean {
  if (stat.isDirectory()) {
    return fs.existsSync(path.join(qPath, 'question.yaml')) || fs.existsSync(path.join(qPath, 'question.json'))
  }
  return qPath.endsWith('.json')
}

function countQuestions(dir: string, subdir: string): number {
  const full = path.join(dir, subdir)
  if (!fs.existsSync(full)) return 0
  try {
    return fs.readdirSync(full).filter((qd) => {
      const qPath = path.join(full, qd)
      try { return isQuestionFile(qPath, fs.statSync(qPath)) } catch { return false }
    }).length
  } catch { return 0 }
}

export function listRuns(): Record<string, unknown>[] {
  if (!fs.existsSync(OUTPUTS_DIR)) return []
  const dirs = findRunDirs(OUTPUTS_DIR)
  return dirs.sort().reverse().map((full) => {
    const meta = loadRunMetadata(full) ?? {}
    const num_approved = countQuestions(full, 'questions')
    const num_rejected = countQuestions(full, 'rejected')
    return {
      run_id: path.basename(full),
      topic: path.basename(full),
      ...meta,
      dir: full,
      // Always recomputed from disk so counts reflect the actual files, not stale metadata.
      num_approved,
      num_rejected,
      num_questions: num_approved + num_rejected,
    }
  })
}

export function loadRunMetadata(dir: string): Record<string, unknown> | null {
  return readJson(path.join(dir, 'run_metadata.json')) ?? readJson(path.join(dir, 'package.json'))
}

function readQuestionFolder(qPath: string): Record<string, unknown> | null {
  const yamlPath = path.join(qPath, 'question.yaml')
  if (fs.existsSync(yamlPath)) return readYaml(yamlPath)
  const jsonPath = path.join(qPath, 'question.json')
  if (fs.existsSync(jsonPath)) return readJson(jsonPath)
  return null
}

export function loadQuestions(dir: string, status: 'approved' | 'rejected' | 'all'): Record<string, unknown>[] {
  const results: Record<string, unknown>[] = []
  const runMeta = loadRunMetadata(dir) ?? {}
  const runId = String(runMeta.run_id ?? path.basename(dir))

  const scanDir = (subdir: string, qStatus: 'approved' | 'rejected') => {
    const full = path.join(dir, subdir)
    if (!fs.existsSync(full)) return
    fs.readdirSync(full).forEach((qd) => {
      const qPath = path.join(full, qd)
      const stat = fs.statSync(qPath)
      let q: Record<string, unknown> | null = null
      let boilerplate_code: string | undefined

      if (stat.isDirectory()) {
        q = readQuestionFolder(qPath)
        if (!q) return
        const bpDir = path.join(qPath, 'boilerplate')
        if (fs.existsSync(bpDir)) {
          const bpFiles = fs.readdirSync(bpDir)
          if (bpFiles.length) {
            try { boilerplate_code = fs.readFileSync(path.join(bpDir, bpFiles[0]), 'utf-8') } catch { /* ignore */ }
          }
        }
      } else if (qd.endsWith('.json')) {
        // Flat-file question format (no per-question subfolder).
        q = readJson(qPath)
        if (!q) return
      } else {
        return
      }

      results.push({
        ...q,
        run_id: runId,
        run_dir: dir,
        status: qStatus,
        boilerplate_code,
      })
    })
  }

  if (status === 'approved' || status === 'all') scanDir('questions', 'approved')
  if (status === 'rejected' || status === 'all') scanDir('rejected', 'rejected')
  return results
}

export function loadReports(dir: string): Record<string, unknown> | null {
  const rDir = path.join(dir, 'reports')
  if (!fs.existsSync(rDir)) return null
  return {
    supervisor: readJson(path.join(rDir, 'supervisor_verdict.json')) ?? {},
    confidence: readJson(path.join(rDir, 'confidence_report.json')) ?? {},
    coverage: readJson(path.join(rDir, 'coverage_matrix.json')) ?? {},
    tokens: readJson(path.join(rDir, 'token_report.json')) ?? {},
  }
}
