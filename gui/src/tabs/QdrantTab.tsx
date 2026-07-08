import { useEffect, useState } from 'react'
import type { QdrantPoint } from '../types'

const DIFF_COLOR: Record<string, string> = {
  easy: 'bg-success/10 text-success',
  medium: 'bg-primary/10 text-primary',
  hard: 'bg-warning/10 text-warning',
}

const PAGE_SIZE = 25

function fmtDate(iso?: string): string {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    return d.toLocaleString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit', hour12: true,
    })
  } catch { return iso }
}

function skillLabel(r: QdrantPoint): string {
  return Array.isArray(r.skill) ? r.skill[0] ?? '—' : r.skill ?? '—'
}

// ---------------------------------------------------------------------------
// Review panel — shown when user clicks Review Selected
// ---------------------------------------------------------------------------
function ReviewPanel({
  selected, rows, onClose,
}: {
  selected: Set<string>
  rows: QdrantPoint[]
  onClose: () => void
}) {
  const questions = rows.filter((r) => selected.has(r.question_id))
  const [reason, setReason] = useState('')
  const [category, setCategory] = useState('quality')
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)

  const submit = async (approved: boolean) => {
    if (!reason.trim()) return
    setSubmitting(true)
    try {
      for (const q of questions) {
        await window.api.review.record(q.question_id, approved, reason, category)
      }
      setDone(true)
    } finally {
      setSubmitting(false)
    }
  }

  if (done) return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="rounded-2xl border border-border bg-surface p-8 shadow-xl w-96 text-center">
        <p className="text-lg font-semibold text-success">Review recorded!</p>
        <p className="mt-1 text-sm text-muted">{questions.length} question{questions.length > 1 ? 's' : ''} reviewed.</p>
        <button onClick={onClose} className="mt-6 rounded-lg bg-primary px-6 py-2 text-sm text-white">Close</button>
      </div>
    </div>
  )

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="rounded-2xl border border-border bg-surface p-6 shadow-xl w-[480px]">
        <h2 className="text-lg font-bold">Review {questions.length} Question{questions.length > 1 ? 's' : ''}</h2>
        <p className="mt-1 text-xs text-muted">{questions.map((q) => q.question_id).join(', ')}</p>

        <div className="mt-4">
          <label className="block text-xs text-muted mb-1">Category</label>
          <select value={category} onChange={(e) => setCategory(e.target.value)}
            className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm outline-none focus:border-primary">
            {['quality', 'difficulty', 'originality', 'scope', 'other'].map((c) => (
              <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>
            ))}
          </select>
        </div>

        <div className="mt-3">
          <label className="block text-xs text-muted mb-1">Reason *</label>
          <textarea value={reason} onChange={(e) => setReason(e.target.value)}
            rows={3} placeholder="Explain why you are approving or rejecting…"
            className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm outline-none focus:border-primary resize-none" />
        </div>

        <div className="mt-4 flex gap-2">
          <button onClick={() => submit(true)} disabled={submitting || !reason.trim()}
            className="flex-1 rounded-lg bg-success px-4 py-2 text-sm font-medium text-white hover:bg-success/90 disabled:opacity-40">
            ✓ Approve
          </button>
          <button onClick={() => submit(false)} disabled={submitting || !reason.trim()}
            className="flex-1 rounded-lg bg-danger px-4 py-2 text-sm font-medium text-white hover:bg-danger/90 disabled:opacity-40">
            ✗ Reject
          </button>
          <button onClick={onClose} className="rounded-lg border border-border px-4 py-2 text-sm text-muted hover:text-text">
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main tab
// ---------------------------------------------------------------------------
export default function QdrantTab() {
  const [rows, setRows] = useState<QdrantPoint[]>([])
  const [filtered, setFiltered] = useState<QdrantPoint[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<'all' | 'approved' | 'rejected'>('all')
  const [diffFilter, setDiffFilter] = useState<string>('all')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [showReview, setShowReview] = useState(false)
  const [exportFmt, setExportFmt] = useState<'xlsx' | 'docx'>('xlsx')
  const [exporting, setExporting] = useState(false)
  const [togglingId, setTogglingId] = useState<string | null>(null)

  const fetchAll = async () => {
    setLoading(true)
    setError(null)
    setSelected(new Set())
    try {
      const all: QdrantPoint[] = []
      let offset: number | null | undefined = undefined
      do {
        const res = await (window.api as any).qdrant.scroll(offset ?? null) as {
          points: QdrantPoint[]
          next_offset: number | null
        }
        all.push(...res.points)
        offset = res.next_offset
      } while (offset != null)
      // sort newest first
      all.sort((a, b) => (b.generated_at ?? '').localeCompare(a.generated_at ?? ''))
      setRows(all)
    } catch (e: any) {
      setError(e?.message ?? 'Failed to load from Qdrant')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void fetchAll() }, [])

  useEffect(() => {
    let result = rows
    if (statusFilter !== 'all') result = result.filter((r) => r.status === statusFilter)
    if (diffFilter !== 'all') result = result.filter((r) => r.difficulty === diffFilter)
    if (search.trim()) {
      const q = search.toLowerCase()
      result = result.filter(
        (r) =>
          r.question_id?.toLowerCase().includes(q) ||
          r.question?.toLowerCase().includes(q) ||
          r.context?.toLowerCase().includes(q) ||
          (Array.isArray(r.skill) ? r.skill.join(' ') : r.skill ?? '').toLowerCase().includes(q),
      )
    }
    setFiltered(result)
    setPage(0)
    setSelected(new Set())
  }, [rows, statusFilter, diffFilter, search])

  const pageRows = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)
  const totalPages = Math.ceil(filtered.length / PAGE_SIZE)

  const toggleRow = (id: string) =>
    setSelected((prev) => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n })

  const allPageSelected = pageRows.length > 0 && pageRows.every((r) => selected.has(r.question_id))
  const togglePage = () => {
    if (allPageSelected) setSelected((prev) => { const n = new Set(prev); pageRows.forEach((r) => n.delete(r.question_id)); return n })
    else setSelected((prev) => { const n = new Set(prev); pageRows.forEach((r) => n.add(r.question_id)); return n })
  }

  const selectAll = () => setSelected(new Set(filtered.map((r) => r.question_id)))
  const clearSelection = () => setSelected(new Set())

  const toggleStatus = async (q: QdrantPoint) => {
    if (q._point_id == null || togglingId === q.question_id) return
    const newStatus = q.status === 'approved' ? 'rejected' : 'approved'
    setTogglingId(q.question_id)
    try {
      await (window.api as any).qdrant.setStatus(q._point_id, newStatus)
      setRows((prev) =>
        prev.map((r) => r.question_id === q.question_id && r._point_id === q._point_id
          ? { ...r, status: newStatus }
          : r
        )
      )
    } catch (e: any) {
      alert(`Failed to update status: ${e?.message}`)
    } finally {
      setTogglingId(null)
    }
  }

  const exportSelected = async () => {
    const qs = filtered.filter((r) => selected.has(r.question_id))
    if (!qs.length) return
    setExporting(true)
    try {
      const rows = qs.map((q) => ({
        question_id: q.question_id,
        topic: q.topic ?? '',
        difficulty: q.difficulty ?? '',
        status: q.status,
        generated_at: q.generated_at ?? '',
        estimated_time_minutes: q.estimated_time_minutes ?? '',
        skill: Array.isArray(q.skill) ? q.skill.join(', ') : (q.skill ?? ''),
        context: q.context ?? '',
        question: q.question ?? '',
        tasks: Array.isArray(q.tasks) ? q.tasks.join('\n') : '',
        files_to_edit: Array.isArray(q.files_to_edit) ? q.files_to_edit.join(', ') : '',
        notes: Array.isArray(q.notes) ? q.notes.join('\n') : '',
      }))
      const defaultName = `qdrant_questions_${new Date().toISOString().slice(0, 10)}`
      await window.api.export.run(rows as any, { format: exportFmt }, defaultName)
    } finally {
      setExporting(false)
    }
  }

  const approved = rows.filter((r) => r.status === 'approved').length
  const rejected = rows.filter((r) => r.status === 'rejected').length

  return (
    <div className="px-10 py-8">
      {showReview && (
        <ReviewPanel selected={selected} rows={filtered} onClose={() => setShowReview(false)} />
      )}

      <h1 className="text-2xl font-bold">Qdrant Cloud</h1>
      <p className="mt-1 text-sm text-muted">All questions stored in Qdrant — approved and rejected, with generation timestamps.</p>

      {/* Stats strip */}
      <div className="mt-4 flex flex-wrap gap-3 items-center">
        {[
          { label: 'Total', value: rows.length, color: 'text-text' },
          { label: 'Approved', value: approved, color: 'text-success' },
          { label: 'Rejected', value: rejected, color: 'text-danger' },
        ].map(({ label, value, color }) => (
          <div key={label} className="rounded-xl border border-border bg-surface px-5 py-3 text-center min-w-[90px]">
            <p className={`text-2xl font-bold ${color}`}>{value}</p>
            <p className="text-xs text-muted">{label}</p>
          </div>
        ))}
        <button onClick={fetchAll} disabled={loading}
          className="ml-auto rounded-lg border border-border px-4 py-2 text-sm text-muted hover:text-text hover:bg-border disabled:opacity-40">
          {loading ? 'Refreshing…' : '↺ Refresh'}
        </button>
      </div>

      {error && (
        <div className="mt-4 rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">{error}</div>
      )}

      {/* Filter bar */}
      <div className="mt-5 flex flex-wrap items-end gap-3 rounded-xl border border-border bg-surface p-4">
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
        <div className="flex-1 min-w-[200px]">
          <label className="block text-xs text-muted">Search</label>
          <input type="text" value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="question, skill, context…"
            className="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm outline-none focus:border-primary" />
        </div>
      </div>

      {/* Selection action bar */}
      {selected.size > 0 && (
        <div className="mt-3 flex flex-wrap items-center gap-3 rounded-xl border border-primary/30 bg-primary/5 px-4 py-3">
          <span className="text-sm font-medium">{selected.size} selected</span>
          <button onClick={selectAll} className="text-xs text-primary hover:underline">Select all {filtered.length}</button>
          <button onClick={clearSelection} className="text-xs text-muted hover:text-text">Clear</button>
          <div className="ml-auto flex items-center gap-2">
            <button onClick={() => setShowReview(true)}
              className="rounded-lg border border-border bg-surface px-3 py-1.5 text-sm hover:bg-border">
              📝 Review
            </button>
            <div className="flex items-center gap-1 rounded-lg border border-border bg-surface px-1 py-1">
              {(['xlsx', 'docx'] as const).map((f) => (
                <button key={f} onClick={() => setExportFmt(f)}
                  className={`rounded px-2 py-1 text-xs uppercase ${exportFmt === f ? 'bg-primary text-white' : 'text-muted hover:text-text'}`}>
                  {f}
                </button>
              ))}
            </div>
            <button onClick={exportSelected} disabled={exporting}
              className="rounded-lg bg-primary px-4 py-1.5 text-sm font-medium text-white hover:bg-primary/90 disabled:opacity-50">
              {exporting ? 'Exporting…' : `⬇ Export ${selected.size}`}
            </button>
          </div>
        </div>
      )}

      {loading && rows.length === 0 && (
        <div className="mt-12 text-center text-muted text-sm">Loading from Qdrant Cloud…</div>
      )}

      {/* Table */}
      {filtered.length > 0 && (
        <div className="mt-4">
          <div className="mb-2 flex items-center justify-between text-sm text-muted">
            <span>{filtered.length} questions{(search || statusFilter !== 'all' || diffFilter !== 'all') ? ' (filtered)' : ''}</span>
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
                  <th className="px-3 py-3 text-left w-8">
                    <input type="checkbox" checked={allPageSelected} onChange={togglePage}
                      className="rounded accent-primary" />
                  </th>
                  {['Question ID', 'Difficulty', 'Skill', 'Topic', 'Status', 'Generated At'].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-medium text-muted">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pageRows.map((q, idx) => {
                  const rowKey = `${q.question_id}-${idx}`
                  const isExpanded = expanded === rowKey
                  const isSelected = selected.has(q.question_id)
                  return (
                    <>
                      <tr key={rowKey}
                        className={`border-b border-border/50 ${isSelected ? 'bg-primary/5' : 'hover:bg-border/20'}`}>
                        <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                          <input type="checkbox" checked={isSelected} onChange={() => toggleRow(q.question_id)}
                            className="rounded accent-primary" />
                        </td>
                        <td className="px-4 py-2 max-w-[200px] truncate font-mono text-xs cursor-pointer font-medium"
                          onClick={() => setExpanded(isExpanded ? null : rowKey)}>
                          {q.question_id}
                        </td>
                        <td className="px-4 py-2 cursor-pointer" onClick={() => setExpanded(isExpanded ? null : rowKey)}>
                          {q.difficulty
                            ? <span className={`rounded px-2 py-0.5 text-xs font-medium ${DIFF_COLOR[q.difficulty] ?? 'bg-border text-muted'}`}>{q.difficulty}</span>
                            : <span className="text-muted text-xs">—</span>}
                        </td>
                        <td className="px-4 py-2 max-w-[140px] truncate text-muted text-xs cursor-pointer"
                          onClick={() => setExpanded(isExpanded ? null : rowKey)}>
                          {skillLabel(q)}
                        </td>
                        <td className="px-4 py-2 max-w-[120px] truncate text-xs cursor-pointer"
                          onClick={() => setExpanded(isExpanded ? null : rowKey)}>
                          {q.topic ?? '—'}
                        </td>
                        <td className="px-4 py-2" onClick={(e) => e.stopPropagation()}>
                          <div className="flex items-center gap-1.5">
                            <span className={`rounded px-2 py-0.5 text-xs font-medium ${q.status === 'approved' ? 'bg-success/10 text-success' : 'bg-danger/10 text-danger'}`}>
                              {q.status}
                            </span>
                            <button
                              title={`Switch to ${q.status === 'approved' ? 'rejected' : 'approved'}`}
                              disabled={togglingId === q.question_id}
                              onClick={() => toggleStatus(q)}
                              className="rounded px-1.5 py-0.5 text-xs border border-border text-muted hover:text-text hover:bg-border disabled:opacity-30 transition-colors">
                              {togglingId === q.question_id ? '…' : '⇄'}
                            </button>
                          </div>
                        </td>
                        <td className="px-4 py-2 text-xs text-muted whitespace-nowrap cursor-pointer"
                          onClick={() => setExpanded(isExpanded ? null : rowKey)}>
                          {fmtDate(q.generated_at)}
                        </td>
                      </tr>

                      {isExpanded && (
                        <tr key={`${rowKey}-detail`}>
                          <td colSpan={7} className="bg-bg px-6 py-4">
                            <div className="space-y-3 text-sm">
                              <div className="flex flex-wrap gap-2 items-center">
                                {q.difficulty && (
                                  <span className={`rounded px-2 py-0.5 text-xs font-medium ${DIFF_COLOR[q.difficulty] ?? ''}`}>{q.difficulty}</span>
                                )}
                                <span className={`rounded px-2 py-0.5 text-xs font-medium ${q.status === 'approved' ? 'bg-success/10 text-success' : 'bg-danger/10 text-danger'}`}>
                                  {q.status}
                                </span>
                                {q.estimated_time_minutes != null && (
                                  <span className="rounded border border-border px-2 py-0.5 text-xs text-muted">~{q.estimated_time_minutes} min</span>
                                )}
                                {q.topic && (
                                  <span className="rounded border border-border px-2 py-0.5 text-xs text-muted">{q.topic}</span>
                                )}
                                {q.generated_at && (
                                  <span className="rounded border border-border px-2 py-0.5 text-xs text-muted">🕐 {fmtDate(q.generated_at)}</span>
                                )}
                              </div>
                              {q.skill && (
                                <p className="text-xs text-muted">
                                  <span className="font-medium text-text">Skill: </span>
                                  {Array.isArray(q.skill) ? q.skill.join(', ') : q.skill}
                                </p>
                              )}
                              {q.context && <p className="text-muted leading-relaxed">{q.context}</p>}
                              {q.question && <p className="font-medium">{q.question}</p>}
                              {q.tasks && q.tasks.length > 0 && (
                                <ol className="list-decimal pl-5 space-y-1 text-muted">
                                  {q.tasks.map((t, i) => <li key={i}>{t}</li>)}
                                </ol>
                              )}
                              {q.files_to_edit && q.files_to_edit.length > 0 && (
                                <div className="flex flex-wrap gap-2">
                                  {q.files_to_edit.map((f) => (
                                    <span key={f} className="rounded bg-border px-2 py-0.5 font-mono text-xs">{f}</span>
                                  ))}
                                </div>
                              )}
                              {q.notes && q.notes.length > 0 && (
                                <ul className="list-disc pl-5 space-y-1 text-xs text-muted">
                                  {q.notes.map((n, i) => <li key={i}>{n}</li>)}
                                </ul>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!loading && rows.length === 0 && !error && (
        <div className="mt-12 text-center text-muted text-sm">No questions found in Qdrant. Run the seed script first.</div>
      )}
    </div>
  )
}
