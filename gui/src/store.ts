import { create } from 'zustand'
import type { AppConfig, TabId, UsageHistoryEntry, PipelineEvent, ProcessExitEvent, RunCompleteEvent, StageDoneEvent } from './types'

interface StatusInfo {
  provider: string
  connected: boolean
  modelRoute: { generator: string; supervisor: string; judge: string }
  dbPath: string
  dbRows: number | null
  sessionCost: number
}

// ── Stage / run state (persists across tab switches) ─────────────────────────

export type StageStatus = 'pending' | 'running' | 'done' | 'failed'
export interface StageState {
  id: string
  label: string
  status: StageStatus
  detail: string
  startedAt?: number
  endedAt?: number
}

interface AcceptedItem { question_id: string; title: string; difficulty: string; confidence: number }
interface RejectedItem { question_id: string; title: string; failure_class: string; issues: string[] }

export interface RunState {
  active: boolean                  // true while a run is in progress or finished (not yet reset)
  running: boolean                 // true while pipeline is still executing
  runId: string | null
  topic: string
  stages: StageState[]
  accepted: AcceptedItem[]
  rejected: RejectedItem[]
  totalCost: number
  summary: RunCompleteEvent | null
  error: { stage: string; message: string } | null
  logs: string[]                   // raw log lines from the CLI
}

const STAGE_DEFS = [
  { id: 'md_summary',       label: 'MD Summary' },
  { id: 'skill_extraction', label: 'Skill Extraction' },
  { id: 'generate',         label: 'Generate Questions' },
  { id: 'supervisor',       label: 'Supervisor Review' },
]

function mkStages(): StageState[] {
  return STAGE_DEFS.map((s) => ({ id: s.id, label: s.label, status: 'pending' as StageStatus, detail: '' }))
}

function initialRunState(): RunState {
  return {
    active: false,
    running: false,
    runId: null,
    topic: '',
    stages: mkStages(),
    accepted: [],
    rejected: [],
    totalCost: 0,
    summary: null,
    error: null,
    logs: [],
  }
}

// ── Full app state ────────────────────────────────────────────────────────────

interface AppState {
  activeTab: TabId | null
  setActiveTab: (tab: TabId | null) => void

  status: StatusInfo
  setStatus: (patch: Partial<StatusInfo>) => void
  addSessionCost: (usd: number) => void

  lastRun: UsageHistoryEntry | null
  hydrate: () => Promise<void>

  // Run state — lives here so tab switches don't lose it
  run: RunState
  startRun: () => void
  resetRun: () => void
  dispatchPipelineEvent: (ev: PipelineEvent | ProcessExitEvent) => void
}

const initialStatus: StatusInfo = {
  provider: 'openrouter',
  connected: false,
  modelRoute: { generator: '—', supervisor: '—', judge: '—' },
  dbPath: 'logs/runs.db',
  dbRows: null,
  sessionCost: 0,
}

export const useStore = create<AppState>((set, get) => ({
  activeTab: null,
  setActiveTab: (tab) => set({ activeTab: tab }),

  status: initialStatus,
  setStatus: (patch) => set((s) => ({ status: { ...s.status, ...patch } })),
  addSessionCost: (usd) =>
    set((s) => ({ status: { ...s.status, sessionCost: s.status.sessionCost + usd } })),

  lastRun: null,

  hydrate: async () => {
    if (!window.api) return
    try {
      const [config, counts, history] = await Promise.all([
        window.api.config.get(),
        window.api.db.rowCounts(),
        window.api.outputs.readUsageHistory().catch(() => [] as UsageHistoryEntry[]),
      ])
      const lastRun = history[0] ?? null
      set((s) => ({
        status: {
          ...s.status,
          provider: config?.provider ?? s.status.provider,
          connected: !!config,
          modelRoute: config?.modelRoute ?? s.status.modelRoute,
          dbPath: config?.dbPath ?? s.status.dbPath,
          dbRows: counts?.runs ?? null,
        },
        lastRun,
      }))
    } catch {
      // silently fail on hydration errors
    }
  },

  // ── Run state ───────────────────────────────────────────────────────────────

  run: initialRunState(),

  startRun: () =>
    set({ run: { ...initialRunState(), active: true, running: true } }),

  resetRun: () =>
    set({ run: initialRunState() }),

  dispatchPipelineEvent: (ev) => {
    set((s) => {
      const run = s.run
      const stages = run.stages.map((st) => ({ ...st }))
      const idxOf = (id: string) => stages.findIndex((st) => st.id === id)

      // Always append to raw logs
      const logLine = JSON.stringify(ev)
      const logs = [...run.logs, logLine]

      switch (ev.event) {
        case 'run_start':
          return { run: { ...run, logs, runId: ev.run_id, topic: ev.topic } }

        case 'stage_start': {
          const i = idxOf(ev.stage)
          if (i < 0) return { run: { ...run, logs } }
          for (let j = 0; j < i; j++)
            if (stages[j].status === 'running') { stages[j].status = 'done'; stages[j].endedAt = Date.now() }
          stages[i].status = 'running'
          if (!stages[i].startedAt) stages[i].startedAt = Date.now()
          if (ev.stage === 'generate' && ev.loop != null) stages[i].detail = `Loop ${ev.loop}, target ${ev.target ?? '?'}`
          if (ev.stage === 'skill_extraction') stages[i].detail = ev.skill_count != null ? `${ev.skill_count} skills found` : ''
          return { run: { ...run, logs, stages } }
        }

        case 'stage_done': {
          const i = idxOf(ev.stage)
          if (i < 0) return { run: { ...run, logs } }
          stages[i].status = 'done'
          stages[i].endedAt = Date.now()
          const parts: string[] = []
          const sdev = ev as StageDoneEvent
          if (ev.stage === 'skill_extraction' && sdev.skill_count != null)
            stages[i].detail = `${sdev.skill_count} skills found`
          else {
            if (sdev.tokens_in) parts.push(`${sdev.tokens_in} in · ${sdev.tokens_out} out`)
            if (sdev.cost != null) parts.push(`$${Number(sdev.cost).toFixed(3)}`)
            if (sdev.verdict) parts.push(sdev.verdict)
            stages[i].detail = parts.join(' · ')
          }
          const addCost = typeof sdev.cost === 'number' ? Number(sdev.cost) : 0
          return { run: { ...run, logs, stages, totalCost: run.totalCost + addCost } }
        }

        case 'stage_progress': {
          const i = idxOf('generate')
          if (i >= 0) stages[i].detail = `Generated ${ev.generated} candidate(s)…`
          return { run: { ...run, logs, stages } }
        }

        case 'question_accepted':
          return {
            run: {
              ...run, logs,
              accepted: [...run.accepted, {
                question_id: ev.question_id,
                title: ev.title,
                difficulty: ev.difficulty,
                confidence: ev.confidence,
              }],
            },
          }

        case 'question_rejected':
          return {
            run: {
              ...run, logs,
              rejected: [...run.rejected, {
                question_id: ev.question_id,
                title: ev.title,
                failure_class: ev.failure_class,
                issues: ev.issues,
              }],
            },
          }

        case 'run_complete':
          stages.forEach((st) => { if (st.status === 'running') { st.status = 'done'; st.endedAt = Date.now() } })
          return { run: { ...run, logs, stages, running: false, summary: ev as RunCompleteEvent } }

        case 'error':
          stages.forEach((st) => { if (st.status === 'running') { st.status = 'failed'; st.endedAt = Date.now() } })
          return { run: { ...run, logs, stages, running: false, error: { stage: ev.stage, message: ev.message } } }

        case 'process_exit':
          if (run.running) {
            stages.forEach((st) => { if (st.status === 'running') st.status = 'failed' })
            return {
              run: {
                ...run, logs, stages, running: false,
                error: { stage: 'process', message: `Pipeline exited (code ${ev.code ?? '?'})` },
              },
            }
          }
          return { run: { ...run, logs } }

        default:
          return { run: { ...run, logs } }
      }
    })

    // Side-effect: track session cost
    if (ev.event === 'stage_done' && typeof (ev as StageDoneEvent).cost === 'number') {
      get().addSessionCost((ev as StageDoneEvent).cost as number)
    }
    if (ev.event === 'run_complete') {
      void get().hydrate()
    }
  },
}))
