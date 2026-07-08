import { useEffect, useState } from 'react'
import KpiStrip from '../dashboard/KpiStrip'
import ChartCard from '../dashboard/ChartCard'
import QuestionsPerRunChart from '../dashboard/charts/QuestionsPerRunChart'
import SupervisorVerdictChart from '../dashboard/charts/SupervisorVerdictChart'
import DifficultyDistributionChart from '../dashboard/charts/DifficultyDistributionChart'
import CostPerRunChart from '../dashboard/charts/CostPerRunChart'
import AgentEventHeatmap from '../dashboard/charts/AgentEventHeatmap'
import ConfidenceHistogram from '../dashboard/charts/ConfidenceHistogram'
import ApprovalByTopicChart from '../dashboard/charts/ApprovalByTopicChart'
import AgentTokenChart from '../dashboard/charts/AgentTokenChart'
import CostPerQuestionChart from '../dashboard/charts/CostPerQuestionChart'
import type {
  DashboardKpis, UsageHistoryEntry, RunOutputMeta, ConfidenceReport, TokenReport, QuestionRow, QuestionTraceRow
} from '../types'
import { COLORS } from '../dashboard/palette'

const SUBTABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'quality', label: 'Quality' },
  { id: 'cost', label: 'Cost & Tokens' },
  { id: 'history', label: 'Run History' },
  { id: 'profiler', label: 'Profiler' },
] as const

interface DashData {
  kpis: DashboardKpis
  history: UsageHistoryEntry[]
  runs: RunOutputMeta[]
  heatmap: { agent: string; status: string; count: number }[]
  confidenceReports: ConfidenceReport[]
  difficultyData: { difficulty: string; count: number }[]
  tokenReports: TokenReport | null
  latestRunDir: string | null
  allQuestions: QuestionRow[]
  rejectionInsights: { category: string; count: number }[]
}

export default function DashboardTab() {
  const [data, setData] = useState<DashData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [sub, setSub] = useState<string>('overview')
  const [expandedRun, setExpandedRun] = useState<string | null>(null)
  const [runEvents, setRunEvents] = useState<Record<string, unknown>[]>([])
  const [questionTraces, setQuestionTraces] = useState<QuestionTraceRow[]>([])
  const [traceView, setTraceView] = useState<'events' | 'traces'>('traces')

  useEffect(() => {
    if (!window.api) return
    Promise.all([
      window.api.db.dashboardKpis(),
      window.api.outputs.readUsageHistory(),
      window.api.outputs.listRuns(),
      window.api.db.agentEventHeatmap(),
    ])
      .then(async ([kpis, history, runs, heatmap]) => {
        // Collect confidence reports from all run dirs
        const confidenceReports: ConfidenceReport[] = []
        const diffMap = new Map<string, number>()
        let tokenReports: TokenReport | null = null
        let latestRunDir: string | null = null

        for (const run of runs.slice(0, 10)) {
          const dir = run.dir
          const reports = await window.api.outputs.loadReports(dir).catch(() => null)
          if (reports?.confidence) {
            confidenceReports.push(reports.confidence as ConfidenceReport)
          }
          if (reports?.tokens && !tokenReports) {
            tokenReports = reports.tokens as TokenReport
            latestRunDir = dir
          }
          // Scan difficulty from questions
          const questions = await window.api.outputs.loadQuestions(dir, 'approved').catch(() => [])
          questions.forEach((q) => {
            const d = String(q.difficulty ?? '')
            if (d) diffMap.set(d, (diffMap.get(d) ?? 0) + 1)
          })
        }

        const difficultyData = [...diffMap.entries()].map(([difficulty, count]) => ({ difficulty, count }))

        // Collect all questions for profiler
        const allQuestionsRaw: QuestionRow[] = []
        for (const run of runs.slice(0, 10)) {
          const qs = await window.api.outputs.loadQuestions(run.dir, 'all').catch(() => [])
          allQuestionsRaw.push(...(qs as QuestionRow[]))
        }

        const rejectionInsights = await window.api.review.getInsights().catch(() => [])

        setData({ kpis, history, runs: runs as RunOutputMeta[], heatmap, confidenceReports, difficultyData, tokenReports, latestRunDir, allQuestions: allQuestionsRaw, rejectionInsights })
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [])

  const handleExpandRun = async (runId: string) => {
    if (expandedRun === runId) { setExpandedRun(null); return }
    setExpandedRun(runId)
    const [events, traces] = await Promise.all([
      window.api.db.runEvents(runId).catch(() => []),
      window.api.db.questionTrace(runId).catch(() => []),
    ])
    setRunEvents(events as Record<string, unknown>[])
    setQuestionTraces(traces as QuestionTraceRow[])
  }

  return (
    <div className="px-10 py-8">
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <p className="mt-1 text-sm text-muted">Analytics across all runs. Primary source: outputs/usage_history.jsonl + run report files.</p>

      {error && (
        <div className="mt-6 rounded-lg border border-danger/40 bg-danger/10 p-4 text-sm text-danger">{error}</div>
      )}
      {!error && !data && (
        <div className="mt-8 text-muted">Loading analytics…</div>
      )}

      {data && (
        <>
          <div className="mt-6"><KpiStrip kpis={data.kpis} /></div>

          {/* Sub-tab row */}
          <div className="mt-8 flex gap-1 border-b border-border">
            {SUBTABS.map((t) => (
              <button key={t.id} onClick={() => setSub(t.id)}
                className={`relative px-4 py-2 text-sm ${sub === t.id ? 'text-text' : 'text-muted hover:text-text'}`}>
                {t.label}
                {sub === t.id && <span className="absolute inset-x-2 -bottom-px h-0.5 rounded bg-primary" />}
              </button>
            ))}
          </div>

          {/* Overview */}
          {sub === 'overview' && (
            <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
              <QuestionsPerRunChart data={data.history} />
              <SupervisorVerdictChart data={data.history} />
              <DifficultyDistributionChart data={data.difficultyData} />
              <CostPerRunChart data={data.history} />
            </div>
          )}

          {/* Quality */}
          {sub === 'quality' && (
            <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
              <div className="col-span-1 lg:col-span-2">
                <AgentEventHeatmap data={data.heatmap} />
              </div>
              <ConfidenceHistogram data={data.confidenceReports} />
              <ApprovalByTopicChart data={data.history} />
            </div>
          )}

          {/* Cost & Tokens */}
          {sub === 'cost' && (
            <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
              <CostPerRunChart data={data.history} />
              <CostPerQuestionChart data={data.history} />
              {data.tokenReports && (
                <div className="col-span-1 lg:col-span-2">
                  <AgentTokenChart data={data.tokenReports} />
                </div>
              )}
              {data.tokenReports?.heaviest_agent && (
                <div className="rounded-xl border border-border bg-surface p-4">
                  <div className="text-xs text-muted">Heaviest Agent (latest run)</div>
                  <div className="mt-2 text-3xl font-bold text-warning">
                    {data.tokenReports.heaviest_agent.replace(/_/g, ' ')}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Profiler */}
          {sub === 'profiler' && (
            <div className="mt-6 space-y-6">
              {/* Rejection patterns */}
              <div className="rounded-xl border border-border bg-surface p-5">
                <h3 className="font-semibold mb-1">Rejection Patterns (continuous learning)</h3>
                <p className="text-xs text-muted mb-4">Human review rejection categories — informs future generation to avoid these patterns.</p>
                {data.rejectionInsights.length === 0 ? (
                  <p className="text-sm text-muted">No human review rejections recorded yet. Use the Review tab to annotate questions.</p>
                ) : (
                  <div className="space-y-2">
                    {data.rejectionInsights.map((ins) => {
                      const total = data.rejectionInsights.reduce((s, i) => s + i.count, 0)
                      const pct = Math.round((ins.count / total) * 100)
                      return (
                        <div key={ins.category} className="flex items-center gap-3">
                          <span className="w-36 text-sm capitalize">{ins.category.replace(/_/g, ' ')}</span>
                          <div className="flex-1 rounded-full bg-border h-2">
                            <div className="rounded-full bg-danger h-2 transition-all" style={{ width: `${pct}%` }} />
                          </div>
                          <span className="w-10 text-right text-xs text-muted">{ins.count}</span>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>

              {/* Domain diversity */}
              <div className="rounded-xl border border-border bg-surface p-5">
                <h3 className="font-semibold mb-1">Question Domain Diversity</h3>
                <p className="text-xs text-muted mb-4">Distribution of generated questions by domain (topic field). Good diversity = balanced spread.</p>
                {(() => {
                  const domainMap = new Map<string, number>()
                  data.allQuestions.forEach((q) => {
                    const d = String(q.topic ?? 'unknown')
                    domainMap.set(d, (domainMap.get(d) ?? 0) + 1)
                  })
                  const entries = [...domainMap.entries()].sort((a, b) => b[1] - a[1])
                  const total = entries.reduce((s, [, c]) => s + c, 0)
                  if (!entries.length) return <p className="text-sm text-muted">No questions loaded.</p>
                  return (
                    <div className="space-y-2">
                      {entries.slice(0, 15).map(([domain, count]) => {
                        const pct = Math.round((count / total) * 100)
                        return (
                          <div key={domain} className="flex items-center gap-3">
                            <span className="w-48 truncate text-xs text-muted" title={domain}>{domain}</span>
                            <div className="flex-1 rounded-full bg-border h-2">
                              <div className="rounded-full bg-primary h-2 transition-all" style={{ width: `${pct}%` }} />
                            </div>
                            <span className="w-10 text-right text-xs text-muted">{count}</span>
                          </div>
                        )
                      })}
                    </div>
                  )
                })()}
              </div>

              {/* Skill coverage profiler */}
              <div className="rounded-xl border border-border bg-surface p-5">
                <h3 className="font-semibold mb-1">Skill Coverage Profile</h3>
                <p className="text-xs text-muted mb-4">How many questions exist per skill across all runs (approved + rejected).</p>
                {(() => {
                  const skillMap = new Map<string, { approved: number; rejected: number }>()
                  data.allQuestions.forEach((q) => {
                    const s = String(q.skill ?? 'unknown')
                    const cur = skillMap.get(s) ?? { approved: 0, rejected: 0 }
                    if (q.status === 'approved') cur.approved++
                    else cur.rejected++
                    skillMap.set(s, cur)
                  })
                  const entries = [...skillMap.entries()].sort((a, b) => (b[1].approved + b[1].rejected) - (a[1].approved + a[1].rejected))
                  if (!entries.length) return <p className="text-sm text-muted">No questions loaded.</p>
                  return (
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="border-b border-border text-left text-muted">
                            <th className="py-2 pr-4">Skill</th>
                            <th className="py-2 pr-3">Approved</th>
                            <th className="py-2 pr-3">Rejected</th>
                            <th className="py-2">Approval %</th>
                          </tr>
                        </thead>
                        <tbody>
                          {entries.slice(0, 20).map(([skill, counts]) => {
                            const total = counts.approved + counts.rejected
                            const pct = total ? Math.round((counts.approved / total) * 100) : 0
                            return (
                              <tr key={skill} className="border-b border-border/30 hover:bg-border/20">
                                <td className="py-1.5 pr-4 max-w-[300px] truncate" title={skill}>{skill}</td>
                                <td className="py-1.5 pr-3 text-success">{counts.approved}</td>
                                <td className="py-1.5 pr-3 text-danger">{counts.rejected}</td>
                                <td className="py-1.5">
                                  <span className={`rounded px-1.5 py-0.5 ${pct >= 70 ? 'bg-success/10 text-success' : pct >= 40 ? 'bg-warning/10 text-warning' : 'bg-danger/10 text-danger'}`}>{pct}%</span>
                                </td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    </div>
                  )
                })()}
              </div>
            </div>
          )}

          {/* Run History */}
          {sub === 'history' && (
            <div className="mt-6">
              <div className="rounded-xl border border-border bg-surface overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      {['Run ID', 'Topic', 'Loop', 'Started', 'Questions', 'Approved', 'Supervisor', 'Score', 'Duration', 'Cost', 'Folder'].map((h) => (
                        <th key={h} className="px-4 py-3 text-left text-xs font-medium text-muted">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.history.map((r) => (
                      <>
                        <tr key={r.run_id}
                          className="cursor-pointer border-b border-border/50 hover:bg-border/20"
                          onClick={() => handleExpandRun(r.run_id)}>
                          <td className="px-4 py-2 font-mono text-xs">{r.run_id.slice(0, 12)}</td>
                          <td className="px-4 py-2 max-w-[150px] truncate">{r.topic}</td>
                          <td className="px-4 py-2">{r.loop_num ?? 1}</td>
                          <td className="px-4 py-2 text-xs text-muted">{String(r.created_at ?? '').slice(0, 16)}</td>
                          <td className="px-4 py-2">{r.num_questions}</td>
                          <td className="px-4 py-2 font-medium text-success">{r.num_approved}</td>
                          <td className="px-4 py-2">
                            <span className={`rounded px-2 py-0.5 text-xs font-medium ${r.supervisor_status === 'APPROVED' ? 'bg-success/10 text-success' : 'bg-danger/10 text-danger'}`}>
                              {r.supervisor_status ?? '—'}
                            </span>
                          </td>
                          <td className="px-4 py-2">{r.num_approved > 0 ? Math.round((r.num_approved / r.num_questions) * 100) + '%' : '—'}</td>
                          <td className="px-4 py-2 text-muted">{r.duration_seconds ? `${r.duration_seconds.toFixed(0)}s` : '—'}</td>
                          <td className="px-4 py-2">{r.estimated_cost_usd ? `$${Number(r.estimated_cost_usd).toFixed(3)}` : '—'}</td>
                          <td className="px-4 py-2">
                            <button onClick={(e) => { e.stopPropagation(); /* runs from output meta don't have dir easily, skip */ }}
                              className="text-xs text-primary hover:underline">Open</button>
                          </td>
                        </tr>
                        {expandedRun === r.run_id && (
                          <tr key={`${r.run_id}-detail`} className="bg-surface/50">
                            <td colSpan={11} className="px-6 py-4">
                              {/* Tab switcher */}
                              <div className="flex gap-2 mb-3">
                                {(['traces', 'events'] as const).map((v) => (
                                  <button key={v} onClick={() => setTraceView(v)}
                                    className={`rounded px-3 py-1 text-xs font-medium ${traceView === v ? 'bg-primary text-white' : 'border border-border text-muted hover:text-text'}`}>
                                    {v === 'traces' ? 'Question Traces' : 'Agent Events'}
                                  </button>
                                ))}
                              </div>

                              {/* Question Traces view */}
                              {traceView === 'traces' && (
                                questionTraces.length === 0 ? (
                                  <p className="text-xs text-muted">No question traces. Traces appear after running with the updated pipeline.</p>
                                ) : (
                                  (() => {
                                    // Group by question_id
                                    const byQ = new Map<string, QuestionTraceRow[]>()
                                    questionTraces.forEach(t => {
                                      const arr = byQ.get(t.question_id) ?? []
                                      arr.push(t)
                                      byQ.set(t.question_id, arr)
                                    })
                                    return (
                                      <div className="space-y-3 max-h-96 overflow-y-auto">
                                        {[...byQ.entries()].map(([qid, traces]) => {
                                          const hasFail = traces.some(t =>
                                            t.decision.includes('fail') || t.decision.includes('violation') ||
                                            t.decision.includes('mismatch') || t.decision.includes('low_realism') ||
                                            t.decision.includes('regenerate')
                                          )
                                          return (
                                            <div key={qid} className={`rounded-lg border p-3 ${hasFail ? 'border-danger/30 bg-danger/5' : 'border-success/20 bg-success/5'}`}>
                                              <p className="font-mono text-xs font-semibold mb-2">{qid}</p>
                                              <div className="space-y-1">
                                                {traces.map((t, i) => (
                                                  <div key={i} className="flex gap-2 text-xs">
                                                    <span className="text-muted w-16 shrink-0">{t.ts.slice(11, 19)}</span>
                                                    <span className="text-primary w-28 shrink-0">{t.agent}</span>
                                                    <span className={`w-32 shrink-0 font-medium ${
                                                      t.decision.includes('fail') || t.decision.includes('violation') || t.decision.includes('mismatch') || t.decision.includes('low_realism') ? 'text-danger'
                                                      : t.decision.includes('ok') || t.decision.includes('pass') ? 'text-success'
                                                      : 'text-warning'
                                                    }`}>{t.decision}</span>
                                                    <span className="text-muted truncate">{t.reason}</span>
                                                  </div>
                                                ))}
                                              </div>
                                            </div>
                                          )
                                        })}
                                      </div>
                                    )
                                  })()
                                )
                              )}

                              {/* Agent Events view */}
                              {traceView === 'events' && (
                                runEvents.length === 0 ? (
                                  <p className="text-xs text-muted">No events recorded in DB.</p>
                                ) : (
                                  <div className="space-y-1 max-h-64 overflow-y-auto">
                                    {runEvents.slice(0, 30).map((ev, i) => (
                                      <div key={i} className="flex gap-3 text-xs">
                                        <span className={`${String(ev.status) === 'fail' ? 'text-danger' : String(ev.status) === 'warn' ? 'text-warning' : 'text-success'}`}>{String(ev.status)}</span>
                                        <span className="text-muted">{String(ev.agent)}</span>
                                        <span className="text-muted">{String(ev.ts ?? '').slice(11, 19)}</span>
                                        <span className="truncate max-w-xs">{String(ev.detail ?? '')}</span>
                                      </div>
                                    ))}
                                  </div>
                                )
                              )}
                            </td>
                          </tr>
                        )}
                      </>
                    ))}
                    {data.history.length === 0 && (
                      <tr><td colSpan={11} className="px-4 py-8 text-center text-muted">No runs yet.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
