import type {
  AppConfig,
  DashboardKpis,
  EvalSet,
  EvalSetMeta,
  EventRow,
  ExportOptions,
  FullConfig,
  LintReport,
  PipelineEvent,
  ProcessExitEvent,
  QuestionRow,
  QuestionTraceRow,
  RunMetadata,
  RunOutputMeta,
  RunReports,
  RunRow,
  UsageHistoryEntry,
} from './types'

export interface AgentEventHeatmapEntry {
  agent: string
  status: string
  count: number
}

export interface Api {
  config: {
    get: () => Promise<AppConfig | null>
    dump: (defaults?: boolean) => Promise<FullConfig>
    write: (changes: Record<string, unknown>) => Promise<void>
  }
  db: {
    rowCounts: () => Promise<{ runs: number; events: number }>
    lastRun: () => Promise<RunRow | null>
    recentRuns: (limit?: number) => Promise<RunRow[]>
    dashboardKpis: () => Promise<DashboardKpis>
    agentEventHeatmap: () => Promise<AgentEventHeatmapEntry[]>
    runEvents: (run_id: string) => Promise<EventRow[]>
    questionTrace: (run_id: string) => Promise<QuestionTraceRow[]>
  }
  outputs: {
    readUsageHistory: () => Promise<UsageHistoryEntry[]>
    listRuns: () => Promise<RunOutputMeta[]>
    loadRunMetadata: (dir: string) => Promise<RunMetadata | null>
    loadQuestions: (dir: string, status: 'approved' | 'rejected' | 'all') => Promise<QuestionRow[]>
    loadReports: (dir: string) => Promise<RunReports | null>
  }
  lint: {
    run: (path: string) => Promise<LintReport>
  }
  run: {
    isRunning: () => Promise<boolean>
    start: (params: RunStartParams) => Promise<void>
    cancel: () => Promise<void>
    onEvent: (cb: (e: PipelineEvent | ProcessExitEvent) => void) => () => void
  }
  export: {
    run: (rows: QuestionRow[], opts: ExportOptions, defaultName: string) => Promise<string | null>
  }
  review: {
    record: (qid: string, approved: boolean, reason: string, reasonCategory?: string) => Promise<void>
    getInsights: () => Promise<{ category: string; count: number }[]>
    listSets: () => Promise<EvalSetMeta[]>
    loadSet: (name: string) => Promise<EvalSet | null>
    saveSet: (set: EvalSet) => Promise<void>
    deleteSet: (name: string) => Promise<void>
  }
  file: {
    showInFolder: (path: string) => Promise<void>
    openFileDialog: (filters: { name: string; extensions: string[] }[]) => Promise<string | null>
  }
  dialog: {
    openFile: (filters: { name: string; extensions: string[] }[]) => Promise<string | null>
  }
  getPathForFile: (file: File) => string
}

export interface RunStartParams {
  mdPath: string
  maxLoops: number
  numQuestions?: number
  diffEasy?: number
  diffMedium?: number
  diffHard?: number
  skipPrompts?: boolean
  humanReview?: boolean
}

declare global {
  interface Window {
    api: Api
  }
}
