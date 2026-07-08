import { spawn, type ChildProcess } from 'node:child_process'
import readline from 'node:readline'
import type { BrowserWindow } from 'electron'
import { REPO_ROOT, resolvePython } from './paths'

let proc: ChildProcess | null = null

export interface RunParams {
  mdPath: string
  maxLoops?: number
  numQuestions?: number
  diffEasy?: number
  diffMedium?: number
  diffHard?: number
  skipPrompts?: boolean
  humanReview?: boolean
}

export function isRunning(): boolean {
  return proc !== null
}

export function startRun(win: BrowserWindow, params: RunParams): void {
  if (proc) throw new Error('A run is already in progress.')
  const py = resolvePython()

  const send = (e: unknown) => {
    if (!win.isDestroyed()) win.webContents.send('run:event', e)
  }

  const args = [
    '-m', 'robo_assess.cli',
    '--config', 'config/config.yaml',
    'generate',
    '--md', params.mdPath,
    '--max-loops', String(params.maxLoops ?? 3),
    '--json-events',
  ]
  if (params.skipPrompts) args.push('--yes')
  if (params.humanReview) args.push('--human-review')

  proc = spawn(py, args, {
    cwd: REPO_ROOT,
    env: { ...process.env, PYTHONUNBUFFERED: '1', PYTHONIOENCODING: 'utf-8' },
  })

  const rl = readline.createInterface({ input: proc.stdout! })
  rl.on('line', (line) => {
    const text = line.trim()
    if (!text) return
    try { send(JSON.parse(text)) } catch { /* non-JSON stdout line — ignore */ }
  })

  let stderrTail = ''
  proc.stderr!.on('data', (d: Buffer) => {
    stderrTail = (stderrTail + d.toString()).slice(-8000)
  })

  proc.on('error', (err) => {
    send({ event: 'error', stage: 'spawn', message: `Failed to start Python: ${err.message}`, retryable: false })
    proc = null
  })

  proc.on('close', (code) => {
    if (code && code !== 0) {
      send({ event: 'error', stage: 'process', message: stderrTail.trim() || `Python exited with code ${code}`, retryable: false })
    }
    send({ event: 'process_exit', code })
    proc = null
  })
}

export function cancelRun(): void {
  if (proc) { proc.kill(); proc = null }
}
