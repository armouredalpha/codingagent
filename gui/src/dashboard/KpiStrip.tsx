import type { DashboardKpis } from '../types'

function Card({ label, value, hint, accent }: { label: string; value: string; hint?: string; accent?: string }) {
  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <div className="text-xs uppercase tracking-wide text-muted">{label}</div>
      <div className="mt-2 text-2xl font-bold" style={accent ? { color: accent } : undefined} title={hint}>
        {value}
      </div>
      {hint && <div className="mt-1 text-xs text-muted">{hint}</div>}
    </div>
  )
}

const pct = (n: number) => `${(n * 100).toFixed(1)}%`
const usd = (n: number) => `$${n.toFixed(n < 0.1 ? 4 : 2)}`

export default function KpiStrip({ kpis }: { kpis: DashboardKpis }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      <Card label="Total Runs" value={String(kpis.totalRuns)} />
      <Card label="Total Questions" value={String(kpis.totalQuestions)} />
      <Card label="Approved" value={String(kpis.approved)} accent="#10b981" hint={`${kpis.approved} questions`} />
      <Card label="Rejected" value={String(kpis.rejected)} accent="#ef4444" />
      <Card label="Approval Rate" value={pct(kpis.approvalRate)} accent="#10b981" />
      <Card label="Avg Cost / Run" value={usd(kpis.avgCostPerRun)} accent="#f59e0b" />
    </div>
  )
}
