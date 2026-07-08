import { CheckCircle2, Circle, Loader2, XCircle } from 'lucide-react'

export type StageStatus = 'pending' | 'running' | 'done' | 'failed'

export interface StageState {
  id: string
  label: string
  status: StageStatus
  detail: string
  startedAt?: number
  endedAt?: number
}

function elapsed(s: StageState, now: number): string {
  if (!s.startedAt) return ''
  const ms = (s.endedAt ?? now) - s.startedAt
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`
}

export default function StageTimeline({ stages, now }: { stages: StageState[]; now: number }) {
  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <h3 className="mb-3 text-sm font-semibold">Pipeline Stages</h3>
      <div className="space-y-3">
        {stages.map((s) => (
          <div key={s.id} className="flex items-start gap-3">
            <div className="mt-0.5 shrink-0">
              {s.status === 'done' && <CheckCircle2 className="h-5 w-5 text-success" />}
              {s.status === 'running' && <Loader2 className="h-5 w-5 animate-spin text-primary" />}
              {s.status === 'failed' && <XCircle className="h-5 w-5 text-danger" />}
              {s.status === 'pending' && <Circle className="h-5 w-5 text-muted/40" />}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline justify-between gap-2">
                <span className={`text-sm font-medium ${
                  s.status === 'running' ? 'text-primary'
                  : s.status === 'done' ? 'text-success'
                  : s.status === 'failed' ? 'text-danger'
                  : 'text-muted'
                }`}>{s.label}</span>
                {s.startedAt && (
                  <span className="shrink-0 text-xs text-muted">{elapsed(s, now)}</span>
                )}
              </div>
              {s.detail && (
                <p className="mt-0.5 truncate text-xs text-muted">{s.detail}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
