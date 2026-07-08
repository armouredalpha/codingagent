import { contextBridge, ipcRenderer, webUtils } from 'electron'

const api = {
  config: {
    get: () => ipcRenderer.invoke('config:get'),
    dump: (defaults?: boolean) => ipcRenderer.invoke('config:dump', defaults),
    write: (changes: Record<string, unknown>) => ipcRenderer.invoke('config:write', changes),
  },
  db: {
    rowCounts: () => ipcRenderer.invoke('db:rowCounts'),
    lastRun: () => ipcRenderer.invoke('db:lastRun'),
    recentRuns: (limit?: number) => ipcRenderer.invoke('db:recentRuns', limit),
    dashboardKpis: () => ipcRenderer.invoke('db:dashboardKpis'),
    agentEventHeatmap: () => ipcRenderer.invoke('db:agentEventHeatmap'),
    runEvents: (run_id: string) => ipcRenderer.invoke('db:runEvents', run_id),
    questionTrace: (run_id: string) => ipcRenderer.invoke('db:questionTrace', run_id),
  },
  outputs: {
    readUsageHistory: () => ipcRenderer.invoke('outputs:readUsageHistory'),
    listRuns: () => ipcRenderer.invoke('outputs:listRuns'),
    loadRunMetadata: (dir: string) => ipcRenderer.invoke('outputs:loadRunMetadata', dir),
    loadQuestions: (dir: string, status: string) =>
      ipcRenderer.invoke('outputs:loadQuestions', dir, status),
    loadReports: (dir: string) => ipcRenderer.invoke('outputs:loadReports', dir),
  },
  lint: {
    run: (path: string) => ipcRenderer.invoke('lint:run', path),
  },
  run: {
    isRunning: () => ipcRenderer.invoke('run:isRunning'),
    start: (params: unknown) => ipcRenderer.invoke('run:start', params),
    cancel: () => ipcRenderer.invoke('run:cancel'),
    onEvent: (cb: (e: unknown) => void) => {
      const listener = (_: unknown, e: unknown) => cb(e)
      ipcRenderer.on('run:event', listener)
      return () => ipcRenderer.removeListener('run:event', listener)
    },
  },
  export: {
    run: (rows: unknown, opts: unknown, defaultName: string) =>
      ipcRenderer.invoke('export:run', rows, opts, defaultName),
  },
  review: {
    record: (qid: string, approved: boolean, reason: string, reasonCategory?: string) =>
      ipcRenderer.invoke('review:record', qid, approved, reason, reasonCategory),
    getInsights: () => ipcRenderer.invoke('review:getInsights'),
    listSets: () => ipcRenderer.invoke('review:listSets'),
    loadSet: (name: string) => ipcRenderer.invoke('review:loadSet', name),
    saveSet: (set: unknown) => ipcRenderer.invoke('review:saveSet', set),
    deleteSet: (name: string) => ipcRenderer.invoke('review:deleteSet', name),
  },
  qdrant: {
    scroll: (offset?: number | null) => ipcRenderer.invoke('qdrant:scroll', offset),
    count: () => ipcRenderer.invoke('qdrant:count'),
    setStatus: (pointId: number, status: 'approved' | 'rejected') =>
      ipcRenderer.invoke('qdrant:setStatus', pointId, status),
  },
  file: {
    showInFolder: (p: string) => ipcRenderer.invoke('file:showInFolder', p),
    openFileDialog: (filters: unknown) => ipcRenderer.invoke('file:openFileDialog', filters),
  },
  dialog: {
    openFile: (filters: unknown) => ipcRenderer.invoke('file:openFileDialog', filters),
  },
  getPathForFile: (file: File) => webUtils.getPathForFile(file),
}

contextBridge.exposeInMainWorld('api', api)
