import { BrowserWindow, dialog, ipcMain, shell } from 'electron'
import fs from 'node:fs'
import path from 'node:path'
import * as db from './db'
import * as outputs from './outputs'
import { readConfig, dumpConfig, writeConfig } from './config'
import { lintFile } from './lint'
import { cancelRun, isRunning, startRun } from './sidecar'
import { buildExport } from './export'
import { handleReview } from './review'

function loadQdrantEnv(): { qdrantUrl: string; qdrantApiKey: string } {
  const envPath = path.join(path.resolve(__dirname, '..', '..'), '.env')
  let qdrantUrl = process.env.QDRANT_URL ?? ''
  let qdrantApiKey = process.env.QDRANT_API_KEY ?? ''
  if (fs.existsSync(envPath)) {
    for (const line of fs.readFileSync(envPath, 'utf-8').split('\n')) {
      const trimmed = line.trim()
      if (!trimmed || trimmed.startsWith('#') || !trimmed.includes('=')) continue
      const [k, ...rest] = trimmed.split('=')
      const v = rest.join('=').trim()
      if (k.trim() === 'QDRANT_URL' && !qdrantUrl) qdrantUrl = v
      if (k.trim() === 'QDRANT_API_KEY' && !qdrantApiKey) qdrantApiKey = v
    }
  }
  return { qdrantUrl, qdrantApiKey }
}

export function registerIpc(): void {
  // Config
  ipcMain.handle('config:get', () => readConfig())
  ipcMain.handle('config:dump', (_e, defaults?: boolean) => dumpConfig(!!defaults))
  ipcMain.handle('config:write', (_e, changes: Record<string, unknown>) => writeConfig(changes))

  // DB
  ipcMain.handle('db:rowCounts', () => db.rowCounts())
  ipcMain.handle('db:lastRun', () => db.lastRun())
  ipcMain.handle('db:recentRuns', (_e, limit?: number) => db.recentRuns(limit))
  ipcMain.handle('db:dashboardKpis', () => db.dashboardKpis())
  ipcMain.handle('db:agentEventHeatmap', () => db.agentEventHeatmap())
  ipcMain.handle('db:runEvents', (_e, run_id: string) => db.runEvents(run_id))
  ipcMain.handle('db:questionTrace', (_e, run_id: string) => db.questionTrace(run_id))

  // Outputs
  ipcMain.handle('outputs:readUsageHistory', () => outputs.readUsageHistory())
  ipcMain.handle('outputs:listRuns', () => outputs.listRuns())
  ipcMain.handle('outputs:loadRunMetadata', (_e, dir: string) => outputs.loadRunMetadata(dir))
  ipcMain.handle('outputs:loadQuestions', (_e, dir: string, status: string) =>
    outputs.loadQuestions(dir, status as 'approved' | 'rejected' | 'all'),
  )
  ipcMain.handle('outputs:loadReports', (_e, dir: string) => outputs.loadReports(dir))

  // Lint
  ipcMain.handle('lint:run', (_e, filePath: string) => lintFile(filePath))

  // Run
  ipcMain.handle('run:isRunning', () => isRunning())
  ipcMain.handle('run:start', (e, params) => {
    const win = BrowserWindow.fromWebContents(e.sender)
    if (!win) throw new Error('No window for run request.')
    startRun(win, params)
  })
  ipcMain.handle('run:cancel', () => cancelRun())

  // Export
  ipcMain.handle('export:run', async (e, rows, opts, defaultName) => {
    const win = BrowserWindow.fromWebContents(e.sender)
    const ext = (opts as { format: string }).format
    const result = await dialog.showSaveDialog(win ?? undefined!, {
      defaultPath: `${defaultName}.${ext}`,
      filters: [{ name: ext.toUpperCase(), extensions: [ext] }],
    })
    if (result.canceled || !result.filePath) return null
    const buf = await buildExport(rows, opts)
    fs.writeFileSync(result.filePath, buf)
    return result.filePath
  })

  // Review
  ipcMain.handle('review:record', (_e, qid: string, approved: boolean, reason: string, reasonCategory?: string) =>
    handleReview.record(qid, approved, reason, reasonCategory),
  )
  ipcMain.handle('review:getInsights', () => handleReview.getInsights())
  ipcMain.handle('review:listSets', () => handleReview.listSets())
  ipcMain.handle('review:loadSet', (_e, name: string) => handleReview.loadSet(name))
  ipcMain.handle('review:saveSet', (_e, set) => handleReview.saveSet(set))
  ipcMain.handle('review:deleteSet', (_e, name: string) => handleReview.deleteSet(name))

  // Qdrant — reads credentials from .env and calls Qdrant REST API
  ipcMain.handle('qdrant:scroll', async (_e, offset?: number | null) => {
    const { qdrantUrl, qdrantApiKey } = loadQdrantEnv()
    if (!qdrantUrl) throw new Error('QDRANT_URL not set in .env')
    const body: Record<string, unknown> = { limit: 100, with_payload: true, with_vector: false }
    if (offset != null) body.offset = offset
    const res = await fetch(`${qdrantUrl}/collections/robo_questions/points/scroll`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(qdrantApiKey ? { 'api-key': qdrantApiKey } : {}) },
      body: JSON.stringify(body),
    })
    if (!res.ok) throw new Error(`Qdrant scroll failed: ${res.status} ${await res.text()}`)
    const json = await res.json() as { result: { points: { id: number; payload: Record<string, unknown> }[]; next_page_offset: unknown } }
    return {
      points: json.result.points.map((p) => ({ ...p.payload, _point_id: p.id })),
      next_offset: json.result.next_page_offset,
    }
  })

  ipcMain.handle('qdrant:setStatus', async (_e, pointId: number, status: 'approved' | 'rejected') => {
    const { qdrantUrl, qdrantApiKey } = loadQdrantEnv()
    if (!qdrantUrl) throw new Error('QDRANT_URL not set in .env')
    const res = await fetch(`${qdrantUrl}/collections/robo_questions/points/payload`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(qdrantApiKey ? { 'api-key': qdrantApiKey } : {}) },
      body: JSON.stringify({ payload: { status }, points: [pointId] }),
    })
    if (!res.ok) throw new Error(`Qdrant setStatus failed: ${res.status} ${await res.text()}`)
    return true
  })

  ipcMain.handle('qdrant:count', async () => {
    const { qdrantUrl, qdrantApiKey } = loadQdrantEnv()
    if (!qdrantUrl) return { total: 0, approved: 0, rejected: 0 }
    const res = await fetch(`${qdrantUrl}/collections/robo_questions`, {
      headers: { ...(qdrantApiKey ? { 'api-key': qdrantApiKey } : {}) },
    })
    if (!res.ok) throw new Error(`Qdrant info failed: ${res.status}`)
    const json = await res.json() as { result: { points_count: number } }
    return { total: json.result.points_count }
  })

  // File
  ipcMain.handle('file:showInFolder', (_e, p: string) => shell.showItemInFolder(p))
  ipcMain.handle('file:openFileDialog', async (e, filters) => {
    const win = BrowserWindow.fromWebContents(e.sender)
    const result = await dialog.showOpenDialog(win ?? undefined!, {
      properties: ['openFile'],
      filters: filters ?? [{ name: 'All Files', extensions: ['*'] }],
    })
    return result.canceled ? null : result.filePaths[0]
  })
}
