import { useEffect, useRef, useState } from 'react'
import StageTimeline from './StageTimeline'
import { useStore } from '../store'
import type { RunStartParams } from '../api'

const DIFFICULTY_COLOR: Record<string, string> = {
  easy: 'text-success',
  medium: 'text-primary',
  hard: 'text-warning',
}

export default function RunExecution({ params, onReset }: { params: RunStartParams; onReset: () => void }) {
  const run = useStore((s) => s.run)
  const startRun = useStore((s) => s.startRun)
  const dispatchPipelineEvent = useStore((s) => s.dispatchPipelineEvent)
  const [now, setNow] = useState(Date.now())
  const [showLogs, setShowLogs] = useState(false)
  const logsEndRef = useRef<HTMLDivElement>(null)
  const started = useRef(false)

  // Clock tick for elapsed time display
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 250)
    return () => clearInterval(t)
  }, [])

  // Auto-scroll raw logs to bottom
  useEffect(() => {
    if (showLogs) logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [run.logs.length, showLogs])

  // Register event listener once at app level — survives tab switches
  useEffect(() => {
    const off = window.api.run.onEvent((raw) => {
      dispatchPipelineEvent(raw as any)
    })
    if (!started.current) {
      started.current = true
      startRun()
      window.api.run.start(params).catch((err: unknown) => {
        dispatchPipelineEvent({
          event: 'error',
          stage: 'spawn',
          message: err instanceof Error ? err.message : String(err),
          retryable: false,
        })
      })
    }
    return off
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Format a raw log line into something human-readable
  const formatLog = (line: string): string => {
    try {
      const ev = JSON.parse(line)
      switch (ev.event) {
        case 'run_start':        return `▶ Run started — topic: ${ev.topic}`
        case 'stage_start':      return `⏳ Stage: ${ev.stage}${ev.loop ? ` (loop ${ev.loop})` : ''}`
        case 'stage_done':       return `✓ Stage done: ${ev.stage}${ev.verdict ? ` → ${ev.verdict}` : ''}${ev.cost != null ? ` ($${Number(ev.cost).toFixed(3)})` : ''}`
        case 'stage_progress':   return `  … ${ev.generated} question(s) generated so far`
        case 'question_accepted':return `✅ ACCEPTED [${ev.difficulty}] ${ev.title} (confidence ${ev.confidence?.toFixed(1)}%)`
        case 'question_rejected':return `❌ REJECTED ${ev.title} — ${ev.failure_class}`
        case 'run_complete':     return `🏁 Run complete — ${ev.supervisor_verdict} (score ${ev.supervisor_score}/100, ${ev.approved}/${ev.generated} approved)`
        case 'error':            return `🔴 ERROR [${ev.stage}]: ${ev.message}`
        case 'process_exit':     return `⚡ Process exited (code ${ev.code ?? '?'})`
        default:                 return line
      }
    } catch {
      return line
    }
  }

  return (
    <div className="px-10 py-8">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Run</h1>
          <p className="mt-1 text-sm text-muted">
            {run.topic ? `Topic: ${run.topic} · ` : ''}
            {run.running ? 'Pipeline running…' : run.error ? 'Run failed' : 'Run complete'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted">
            Cost: <span className="font-medium text-text">${run.totalCost.toFixed(3)}</span>
          </span>
          <button
            onClick={() => setShowLogs((v) => !v)}
            className="rounded-lg border border-border px-4 py-2 text-sm hover:border-primary"
          >
            {showLogs ? 'Hide Logs' : 'Show Logs'}
          </button>
          {run.running ? (
            <button
              onClick={() => window.api.run.cancel()}
              className="rounded-lg border border-border px-4 py-2 text-sm hover:border-danger hover:text-danger"
            >
              Cancel
            </button>
          ) : (
            <button
              onClick={onReset}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/90"
            >
              New run
            </button>
          )}
        </div>
      </div>

      {/* Raw log panel */}
      {showLogs && (
        <div className="mb-6 rounded-xl border border-border bg-[#0d0d0d] p-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">
            Pipeline Logs ({run.logs.length} events)
          </p>
          <div className="h-64 overflow-y-auto font-mono text-xs leading-relaxed text-green-400">
            {run.logs.length === 0 ? (
              <span className="text-muted">Waiting for events…</span>
            ) : (
              run.logs.map((line, i) => (
                <div key={i} className="py-[1px]">
                  <span className="mr-2 text-muted select-none">{String(i + 1).padStart(3, '0')}</span>
                  {formatLog(line)}
                </div>
              ))
            )}
            <div ref={logsEndRef} />
          </div>
        </div>
      )}

      {/* Stage timeline + live question feed */}
      <div className="grid grid-cols-[220px_1fr] gap-6">
        <StageTimeline stages={run.stages} now={now} />

        <div className="space-y-3">
          {run.accepted.map((q) => (
            <div key={q.question_id} className="rounded-xl border border-success/30 bg-success/5 p-4">
              <div className="flex items-center gap-2">
                <span className={`text-xs font-medium uppercase ${DIFFICULTY_COLOR[q.difficulty] ?? 'text-muted'}`}>
                  {q.difficulty}
                </span>
                <span className="text-xs text-muted">confidence {q.confidence.toFixed(1)}%</span>
              </div>
              <p className="mt-1 text-sm font-medium text-success">{q.title}</p>
            </div>
          ))}
          {run.rejected.map((q, i) => (
            <details key={`${q.question_id}-${i}`} className="rounded-xl border border-danger/30 bg-danger/5 p-4">
              <summary className="cursor-pointer text-sm font-medium text-danger">
                {q.title} — {q.failure_class}
              </summary>
              <ul className="mt-2 space-y-1">
                {q.issues.map((iss, j) => <li key={j} className="text-xs text-muted">• {iss}</li>)}
              </ul>
            </details>
          ))}
          {run.accepted.length === 0 && run.rejected.length === 0 && run.running && (
            <div className="flex h-40 items-center justify-center rounded-xl border border-border text-sm text-muted">
              Waiting for questions…
            </div>
          )}
        </div>
      </div>

      {/* Error */}
      {run.error && (
        <div className="mt-6 rounded-xl border border-danger/40 bg-danger/10 p-4 text-sm text-danger">
          <p className="font-semibold">Pipeline error ({run.error.stage})</p>
          <p className="mt-1 whitespace-pre-wrap">{run.error.message}</p>
        </div>
      )}

      {/* Summary */}
      {run.summary && (
        <div className="mt-6 rounded-xl border border-border bg-surface p-6">
          <div className={`mb-4 inline-flex rounded-lg px-4 py-2 text-lg font-bold ${
            run.summary.supervisor_verdict === 'APPROVED'
              ? 'bg-success/10 text-success'
              : 'bg-danger/10 text-danger'
          }`}>
            {run.summary.supervisor_verdict}
          </div>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div><div className="text-xs text-muted">Validation Score</div><div className="text-2xl font-bold">{run.summary.supervisor_score}/100</div></div>
            <div><div className="text-xs text-muted">Generated</div><div className="text-2xl font-bold">{run.summary.generated}</div></div>
            <div><div className="text-xs text-muted">Approved</div><div className="text-2xl font-bold text-success">{run.summary.approved}</div></div>
            <div><div className="text-xs text-muted">Coverage</div><div className="text-2xl font-bold">{run.summary.coverage_pct.toFixed(0)}%</div></div>
          </div>
          {Object.keys(run.summary.cost_breakdown).length > 0 && (
            <div className="mt-4 rounded-lg border border-border p-3">
              <p className="mb-2 text-xs text-muted">Cost breakdown</p>
              <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs">
                {Object.entries(run.summary.cost_breakdown).map(([k, v]) => (
                  <span key={k}>
                    <span className="text-muted">{k}</span>{' '}
                    <span className="font-medium">${Number(v).toFixed(3)}</span>
                  </span>
                ))}
              </div>
            </div>
          )}
          <div className="mt-4 flex gap-2">
            <button
              onClick={() => window.api.file.showInFolder(run.summary!.output_dir)}
              className="rounded-lg border border-border px-4 py-2 text-sm hover:border-primary"
            >
              Open Output Folder
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
