import fs from 'node:fs'
import { spawn } from 'node:child_process'
import YAML from 'yaml'
import { CONFIG_PATH, REPO_ROOT, resolvePython } from './paths'

export function readConfig() {
  if (!fs.existsSync(CONFIG_PATH)) return null
  const c = YAML.parse(fs.readFileSync(CONFIG_PATH, 'utf-8')) ?? {}
  const model = c.model ?? '—'
  const agentModels: Record<string, string> = c.agent_models ?? {}
  return {
    provider: c.provider ?? 'openrouter',
    connected: true,
    modelRoute: {
      generator: agentModels['question_generator'] ?? model,
      supervisor: agentModels['supervisor_judge'] ?? model,
      judge: agentModels['quality_judge'] ?? model,
    },
    dbPath: c.log_db_path ?? 'logs/runs.db',
    dbRows: null,
    sessionCost: 0,
  }
}

export function dumpConfig(defaults = false): Promise<unknown> {
  return new Promise((resolve, reject) => {
    if (!defaults) {
      try {
        if (!fs.existsSync(CONFIG_PATH)) return resolve({})
        resolve(YAML.parse(fs.readFileSync(CONFIG_PATH, 'utf-8')) ?? {})
      } catch (e) { reject(e) }
      return
    }
    const py = resolvePython()
    const proc = spawn(py, ['-c', `
import json, sys
sys.path.insert(0, '.')
from robo_assess.config import Settings
s = Settings()
print(json.dumps(s.model_dump()))
`], { cwd: REPO_ROOT, env: { ...process.env, PYTHONIOENCODING: 'utf-8' } })
    let out = ''
    let err = ''
    proc.stdout.on('data', (d: Buffer) => (out += d.toString()))
    proc.stderr.on('data', (d: Buffer) => (err += d.toString()))
    proc.on('close', (code) => {
      try { resolve(JSON.parse(out.trim())) }
      catch { reject(new Error(err.trim() || `config dump failed (code ${code})`)) }
    })
    proc.on('error', (e) => reject(e))
  })
}

export function writeConfig(changes: Record<string, unknown>): void {
  if (!fs.existsSync(CONFIG_PATH)) return
  const doc = YAML.parseDocument(fs.readFileSync(CONFIG_PATH, 'utf-8'))
  for (const [path, value] of Object.entries(changes)) {
    doc.setIn(path.split('.'), value)
  }
  fs.writeFileSync(CONFIG_PATH, doc.toString(), 'utf-8')
}
