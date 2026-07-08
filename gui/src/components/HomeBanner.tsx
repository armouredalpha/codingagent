import { BarChart3, CheckCircle2, Database, Play, Sliders, type LucideIcon } from 'lucide-react'
import { useStore } from '../store'
import type { TabId } from '../types'

const CARDS: { id: TabId; title: string; desc: string; Icon: LucideIcon }[] = [
  { id: 'run', title: 'New Run', desc: 'Upload a teaching material and generate ROS2 questions', Icon: Play },
  { id: 'questions', title: 'Browse Questions', desc: 'Query, filter, and export generated questions', Icon: Database },
  { id: 'dashboard', title: 'Dashboard', desc: 'Analytics across all runs — cost, quality, approval rates', Icon: BarChart3 },
  { id: 'config', title: 'Configure', desc: 'Model routing, quality gates, and generation settings', Icon: Sliders },
  { id: 'review', title: 'Review', desc: 'Instructor review with annotations and eval sets', Icon: CheckCircle2 },
]

export default function HomeBanner() {
  const setActiveTab = useStore((s) => s.setActiveTab)
  const lastRun = useStore((s) => s.lastRun)
  const status = useStore((s) => s.status)

  return (
    <div className="mx-auto max-w-5xl px-10 py-12">
      <p className="text-sm font-medium uppercase tracking-widest text-primary">
        NxtWave Robotics Engineering
      </p>
      <h1 className="mt-2 text-4xl font-bold">Robo Assess</h1>
      <p className="mt-2 text-lg text-muted">ROS2 Coding Question Generator</p>
      <p className="mt-4 max-w-3xl leading-relaxed text-muted">
        Multi-agent pipeline that transforms Markdown teaching materials into high-quality
        ROS2 coding questions. Runs skill extraction → question generation → confidence
        gating → supervisor validation automatically.
      </p>

      {/* Stat chips */}
      <div className="mt-8 flex flex-wrap gap-3">
        {[
          { label: 'Total Runs', value: status.dbRows != null ? String(status.dbRows) : '—' },
          { label: 'Total Questions', value: lastRun ? String(lastRun.num_questions ?? 0) : '—' },
          { label: 'Approved', value: lastRun ? String(lastRun.num_approved ?? 0) : '—' },
        ].map(({ label, value }) => (
          <div key={label} className="rounded-lg border border-border bg-surface px-4 py-2">
            <div className="text-xs text-muted">{label}</div>
            <div className="text-xl font-bold">{value}</div>
          </div>
        ))}
      </div>

      {/* Quick action cards */}
      <div className="mt-10 grid grid-cols-2 gap-4 lg:grid-cols-3">
        {CARDS.map(({ id, title, desc, Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className="flex items-start gap-4 rounded-xl border border-border bg-surface p-5 text-left transition-colors hover:border-primary"
          >
            <Icon className="h-6 w-6 shrink-0 text-primary" />
            <span>
              <span className="block font-semibold">{title}</span>
              <span className="mt-1 block text-sm text-muted">{desc}</span>
            </span>
          </button>
        ))}
      </div>

      {/* Last run card */}
      <div className="mt-10 rounded-xl border border-border bg-surface p-5">
        <p className="text-sm font-medium">Last run</p>
        {lastRun ? (
          <div className="mt-3 space-y-2">
            <div className="flex flex-wrap gap-x-8 gap-y-2 text-sm">
              <span><span className="text-muted">Run ID</span>{' '}<span className="font-mono">{lastRun.run_id}</span></span>
              <span><span className="text-muted">Topic</span>{' '}<span className="font-medium">{lastRun.topic}</span></span>
              <span>
                <span className="text-muted">Supervisor</span>{' '}
                <span className={`font-semibold ${lastRun.supervisor_status === 'APPROVED' ? 'text-success' : 'text-danger'}`}>
                  {lastRun.supervisor_status ?? '—'}
                </span>
              </span>
              <span><span className="text-muted">Approved</span>{' '}<span className="font-medium text-success">{lastRun.num_approved}/{lastRun.num_questions}</span></span>
              <span><span className="text-muted">Cost</span>{' '}<span className="font-medium">${Number(lastRun.estimated_cost_usd ?? 0).toFixed(3)}</span></span>
              <span><span className="text-muted">When</span>{' '}<span className="font-medium">{String(lastRun.created_at ?? '').slice(0, 19)}</span></span>
            </div>
          </div>
        ) : (
          <p className="mt-1 text-sm text-muted">No runs recorded yet. Start by clicking "New Run".</p>
        )}
      </div>
    </div>
  )
}
