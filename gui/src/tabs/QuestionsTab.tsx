import { useEffect, useState } from 'react'
import type { QuestionRow, RunOutputMeta } from '../types'

const DIFF_COLOR: Record<string, string> = {
  easy: 'bg-success/10 text-success',
  medium: 'bg-primary/10 text-primary',
  hard: 'bg-warning/10 text-warning',
}

const PAGE_SIZE = 25

export default function QuestionsTab() {
  const [runs, setRuns] = useState<RunOutputMeta[]>([])
  const [selectedRuns, setSelectedRuns] = useState<string[]>([])
  const [statusFilter, setStatusFilter] = useState<'all' | 'approved' | 'rejected'>('approved')
  const [diffFilter, setDiffFilter] = useState<string>('all')
  const [rows, setRows] = useState<QuestionRow[]>([])
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(0)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [exportFormat, setExportFormat] = useState<'json' | 'xlsx' | 'docx'>('json')
  const [includeSolution, setIncludeSolution] = useState(false)
  const [dbInfo, setDbInfo] = useState<{ exists: boolean; runCount: number } | null>(null)
  const [dbExpanded, setDbExpanded] = useState(false)

  useEffect(() => {
    window.api?.outputs.listRuns().then((r) => setRuns(r as RunOutputMeta[])).catch(() => {})
    window.api?.db.rowCounts().then((c) => setDbInfo({ exists: true, runCount: c.runs })).catch(() => {})
  }, [])

  const fetch = async () => {
    setLoading(true)
    setPage(0)
    try {
      const dirs = selectedRuns.length
        ? runs.filter((r) => selectedRuns.includes(r.run_id)).map((r) => r.dir)
        : runs.map((r) => r.dir)
      const allRows: QuestionRow[] = []
      for (const dir of dirs) {
        const qs = await window.api.outputs.loadQuestions(dir, statusFilter)
        allRows.push(...(qs as QuestionRow[]))
      }
      const filtered = diffFilter === 'all' ? allRows : allRows.filter((q) => q.difficulty === diffFilter)
      setRows(filtered)
    } finally {
      setLoading(false)
    }
  }

  const pageRows = rows.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)
  const totalPages = Math.ceil(rows.length / PAGE_SIZE)

  const onExport = async () => {
    if (!rows.length) return
    const defaultName = `robo_assess_questions_${new Date().toISOString().slice(0, 10)}`
    await window.api.export.run(rows as unknown as QuestionRow[], { format: exportFormat, includeSolution }, defaultName)
  }

  return (
    <div className="px-10 py-8">
      <h1 className="text-2xl font-bold">Questions</h1>
      <p className="mt-1 text-sm text-muted">Browse, filter, and export generated questions from all runs.</p>

      {/* Filter bar */}
      <div className="mt-6 flex flex-wrap items-end gap-3 rounded-xl border border-border bg-surface p-4">
        <div>
          <label className="block text-xs text-muted">Run</label>
          <select value={selectedRuns[0] ?? '__all__'}
            onChange={(e) => setSelectedRuns(e.target.value === '__all__' ? [] : [e.target.value])}
            className="mt-1 w-56 rounded-lg border border-border bg-bg px-3 py-2 text-sm outline-none focus:border-primary">
            <option value="__all__">All runs ({runs.length})</option>
            {runs.map((r) => (
              <option key={r.run_id} value={r.run_id}>
                {r.topic.slice(0, 28)} · {r.num_approved}✓ {r.num_rejected}✗
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-muted">Status</label>
          <div className="mt-1 flex gap-1">
            {(['all', 'approved', 'rejected'] as const).map((s) => (
              <button key={s} onClick={() => setStatusFilter(s)}
                className={`rounded-lg px-3 py-1.5 text-sm capitalize ${statusFilter === s ? 'bg-primary text-white' : 'border border-border text-muted hover:text-text'}`}>
                {s}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label className="block text-xs text-muted">Difficulty</label>
          <div className="mt-1 flex gap-1">
            {(['all', 'easy', 'medium', 'hard'] as const).map((d) => (
              <button key={d} onClick={() => setDiffFilter(d)}
                className={`rounded-lg px-3 py-1.5 text-sm capitalize ${diffFilter === d ? 'bg-primary text-white' : 'border border-border text-muted hover:text-text'}`}>
                {d}
              </button>
            ))}
          </div>
        </div>
        <button onClick={fetch} disabled={loading}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/90 disabled:opacity-50">
          {loading ? 'Loading…' : 'Fetch Questions'}
        </button>
      </div>

      {/* Results table */}
      {rows.length > 0 && (
        <div className="mt-4">
          <div className="mb-2 flex items-center justify-between text-sm text-muted">
            <span>{rows.length} questions</span>
            <div className="flex items-center gap-2">
              <button disabled={page === 0} onClick={() => setPage((p) => p - 1)}
                className="rounded px-2 py-1 hover:bg-border disabled:opacity-30">←</button>
              <span>{page + 1}/{totalPages}</span>
              <button disabled={page >= totalPages - 1} onClick={() => setPage((p) => p + 1)}
                className="rounded px-2 py-1 hover:bg-border disabled:opacity-30">→</button>
            </div>
          </div>

          <div className="rounded-xl border border-border bg-surface overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  {['Title', 'Difficulty', 'Skill', 'Topic', 'Run', 'Status', 'Date'].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-medium text-muted">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pageRows.map((q) => (
                  <>
                    <tr key={q.question_id}
                      className="cursor-pointer border-b border-border/50 hover:bg-border/20"
                      onClick={() => setExpanded(expanded === q.question_id ? null : q.question_id)}>
                      <td className="px-4 py-2 max-w-[200px] truncate font-medium">{q.question_id}</td>
                      <td className="px-4 py-2">
                        <span className={`rounded px-2 py-0.5 text-xs font-medium ${DIFF_COLOR[q.difficulty] ?? ''}`}>{q.difficulty}</span>
                      </td>
                      <td className="px-4 py-2 max-w-[120px] truncate text-muted text-xs">{q.skill}</td>
                      <td className="px-4 py-2 max-w-[120px] truncate">{q.topic}</td>
                      <td className="px-4 py-2 font-mono text-xs text-muted">{q.run_id.slice(0, 10)}</td>
                      <td className="px-4 py-2">
                        <span className={`rounded px-2 py-0.5 text-xs ${q.status === 'approved' ? 'text-success' : 'text-danger'}`}>{q.status}</span>
                      </td>
                      <td className="px-4 py-2 text-xs text-muted">—</td>
                    </tr>
                    {expanded === q.question_id && (
                      <tr key={`${q.question_id}-detail`}>
                        <td colSpan={7} className="bg-bg px-6 py-4">
                          <div className="space-y-3 text-sm">
                            <div className="flex flex-wrap gap-2">
                              <span className={`rounded px-2 py-0.5 text-xs font-medium ${DIFF_COLOR[q.difficulty] ?? ''}`}>{q.difficulty}</span>
                              <span className="rounded border border-border px-2 py-0.5 text-xs text-muted">{q.skill}</span>
                              <span className="rounded border border-border px-2 py-0.5 text-xs text-muted">~{q.estimated_time_minutes ?? '?'} min</span>
                            </div>
                            {q.context && <p className="text-muted leading-relaxed">{q.context}</p>}
                            <p className="font-medium">{q.question}</p>
                            {q.tasks?.length > 0 && (
                              <ol className="list-decimal pl-5 space-y-1 text-muted">
                                {q.tasks.map((t, i) => <li key={i}>{t}</li>)}
                              </ol>
                            )}
                            {q.files_to_edit?.length > 0 && (
                              <div className="flex flex-wrap gap-2">
                                {q.files_to_edit.map((f) => (
                                  <span key={f} className="rounded bg-border px-2 py-0.5 font-mono text-xs">{f}</span>
                                ))}
                              </div>
                            )}
                            {q.notes?.length > 0 && (
                              <ul className="list-disc pl-5 space-y-1 text-xs text-muted">
                                {q.notes.map((n, i) => <li key={i}>{n}</li>)}
                              </ul>
                            )}
                            {q.boilerplate_code && (
                              <div className="relative">
                                <div className="flex items-center justify-between mb-1">
                                  <span className="text-xs text-muted">Boilerplate</span>
                                  <button onClick={() => navigator.clipboard.writeText(q.boilerplate_code!)}
                                    className="text-xs text-primary hover:underline">Copy</button>
                                </div>
                                <pre className="overflow-auto rounded-lg bg-surface p-3 text-xs font-mono max-h-64 border border-border">{q.boilerplate_code}</pre>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Export bar */}
      {rows.length > 0 && (
        <div className="mt-4 flex flex-wrap items-center gap-3 rounded-xl border border-border bg-surface p-4">
          <div className="flex gap-1">
            {(['json', 'xlsx', 'docx'] as const).map((f) => (
              <button key={f} onClick={() => setExportFormat(f)}
                className={`rounded px-3 py-1.5 text-sm uppercase ${exportFormat === f ? 'bg-primary text-white' : 'border border-border text-muted hover:text-text'}`}>
                {f}
              </button>
            ))}
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={includeSolution} onChange={(e) => setIncludeSolution(e.target.checked)} className="rounded accent-primary" />
            Include solution
          </label>
          <button onClick={onExport} className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/90">
            Export {rows.length} Questions
          </button>
        </div>
      )}

      {/* DB status panel */}
      <div className="mt-6">
        <button onClick={() => setDbExpanded((o) => !o)} className="flex items-center gap-2 text-sm text-muted hover:text-text">
          <span>DB Status</span>
          <span>{dbExpanded ? '▲' : '▼'}</span>
        </button>
        {dbExpanded && (
          <div className="mt-2 rounded-xl border border-border bg-surface p-4 text-sm">
            <p><span className="text-muted">Path:</span> logs/runs.db</p>
            <p><span className="text-muted">Runs:</span> {dbInfo?.runCount ?? '—'}</p>
            <button onClick={() => window.api.file.showInFolder('logs/')} className="mt-2 text-xs text-primary hover:underline">Open DB folder</button>
          </div>
        )}
      </div>
    </div>
  )
}
