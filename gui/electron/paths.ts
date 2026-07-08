import path from 'node:path'
import fs from 'node:fs'

// gui/dist-electron/ → gui/ → project root
export const REPO_ROOT = path.resolve(__dirname, '..', '..')
export const DB_PATH = path.join(REPO_ROOT, 'logs', 'runs.db')
export const CONFIG_PATH = path.join(REPO_ROOT, 'config', 'config.yaml')
export const OUTPUTS_DIR = path.join(REPO_ROOT, 'outputs')
export const CALIBRATION_DIR = path.join(REPO_ROOT, 'calibration')

export function resolvePython(): string {
  const override = process.env.ROBO_PYTHON ?? process.env.MCQ_PYTHON
  if (override && fs.existsSync(override)) return override
  const candidates =
    process.platform === 'win32'
      ? [path.join(REPO_ROOT, '.venv', 'Scripts', 'python.exe'), path.join(REPO_ROOT, 'venv', 'Scripts', 'python.exe')]
      : [path.join(REPO_ROOT, '.venv', 'bin', 'python'), path.join(REPO_ROOT, 'venv', 'bin', 'python')]
  for (const c of candidates) if (fs.existsSync(c)) return c
  return process.platform === 'win32' ? 'python.exe' : 'python3'
}
