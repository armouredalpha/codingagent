import { useEffect, useState } from 'react'
import type { EvalQuestion, EvalSet, EvalSetMeta, RunOutputMeta } from '../types'

const DIFF_COLOR: Record<string, string> = {
  easy: 'bg-success/10 text-success',
  medium: 'bg-primary/10 text-primary',
  hard: 'bg-warning/10 text-warning',
}

const REJECTION_REASONS = [
  { value: 'too_easy', label: 'Too Easy' },
  { value: 'too_vague', label: 'Too Vague' },
  { value: 'wrong_domain', label: 'Wrong Domain' },
  { value: 'duplicate', label: 'Duplicate / Similar' },
  { value: 'bad_boilerplate', label: 'Bad Boilerplate' },
  { value: 'wrong_difficulty', label: 'Wrong Difficulty' },
  { value: 'off_topic', label: 'Off Topic' },
  { value: 'poor_quality', label: 'Poor Quality' },
  { value: 'other', label: 'Other' },
]

function toYaml(q: EvalQuestion): string {
  const fields: Record<string, unknown> = {
    question_id: q.question_id,
    topic: q.topic,
    difficulty: q.difficulty,
    estimated_time_minutes: q.estimated_time_minutes,
    skill: q.skill,
    context: q.context,
    question: q.question,
    files_to_edit: q.files_to_edit,
    tasks: q.tasks,
    notes: q.notes,
  }
  if (q.boilerplate_code) fields.boilerplate_code = q.boilerplate_code
  const lines: string[] = []
  for (const [k, v] of Object.entries(fields)) {
    if (v == null) continue
    if (Array.isArray(v)) {
      if (!v.length) continue
      lines.push(`${k}:`)
      v.forEach((item) => lines.push(`  - ${String(item).replace(/\n/g, '\n    ')}`))
    } else if (typeof v === 'string' && v.includes('\n')) {
      lines.push(`${k}: |`)
      v.split('\n').forEach((line) => lines.push(`  ${line}`))
    } else {
      lines.push(`${k}: ${v}`)
    }
  }
  return lines.join('\n')
}

interface QuestionCardProps {
  q: EvalQuestion
  onDecision: (qid: string, approved: boolean, notes: string, reasonCategory: string) => void
  onUpdateNotes: (qid: string, notes: string) => void
  onUpdateReason: (qid: string, reason: string) => void
  reason: string
}

function QuestionCard({ q, onDecision, onUpdateNotes, onUpdateReason, reason }: QuestionCardProps) {
  const [showYaml, setShowYaml] = useState(false)

  return (
    <div className={`rounded-xl border p-5 transition-colors ${
      q.annotation.approved === true ? 'border-success/30 bg-success/5'
      : q.annotation.approved === false ? 'border-danger/30 bg-danger/5'
      : 'border-border bg-surface'
    }`}>
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap gap-2 mb-2">
            <span className={`rounded px-2 py-0.5 text-xs font-medium ${DIFF_COLOR[q.difficulty] ?? ''}`}>{q.difficulty}</span>
            <span className="rounded border border-border px-2 py-0.5 text-xs text-muted">{q.skill}</span>
            {q.estimated_time_minutes && (
              <span className="rounded border border-border px-2 py-0.5 text-xs text-muted">~{q.estimated_time_minutes} min</span>
            )}
            <span className={`rounded px-2 py-0.5 text-xs font-medium ${q.status === 'approved' ? 'text-success bg-success/10' : 'text-danger bg-danger/10'}`}>
              AI: {q.status}
            </span>
            {q.annotation.approved !== null && (
              <span className={`rounded px-2 py-0.5 text-xs font-medium ${q.annotation.approved ? 'text-success bg-success/20' : 'text-danger bg-danger/20'}`}>
                Human: {q.annotation.approved ? 'approved' : 'rejected'}
              </span>
            )}
          </div>
          <p className="text-sm font-semibold text-text">{q.question_id}</p>
        </div>

        {/* Action buttons */}
        <div className="flex shrink-0 flex-col gap-1.5">
          <button
            onClick={() => onDecision(q.question_id, true, q.annotation.notes, reason)}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${q.annotation.approved === true ? 'bg-success text-white' : 'border border-success/40 text-success hover:bg-success/10'}`}>
            ✓ Approve
          </button>
          <button
            onClick={() => onDecision(q.question_id, false, q.annotation.notes, reason)}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${q.annotation.approved === false ? 'bg-danger text-white' : 'border border-danger/40 text-danger hover:bg-danger/10'}`}>
            ✗ Reject
          </button>
          <button
            onClick={() => setShowYaml((s) => !s)}
            className="rounded-lg border border-border px-3 py-1.5 text-xs text-muted hover:text-text">
            {showYaml ? 'Hide YAML' : 'View YAML'}
          </button>
        </div>
      </div>

      {/* Full question content */}
      <div className="mt-4 space-y-3 text-sm">
        {q.context && (
          <div>
            <p className="text-xs font-medium text-muted mb-1">Context</p>
            <p className="text-text leading-relaxed">{q.context}</p>
          </div>
        )}
        <div>
          <p className="text-xs font-medium text-muted mb-1">Question</p>
          <p className="font-medium text-text leading-relaxed">{q.question}</p>
        </div>
        {q.tasks?.length > 0 && (
          <div>
            <p className="text-xs font-medium text-muted mb-1">Tasks</p>
            <ol className="list-decimal pl-5 space-y-1">
              {q.tasks.map((t, i) => <li key={i} className="text-text">{t}</li>)}
            </ol>
          </div>
        )}
        {q.files_to_edit?.length > 0 && (
          <div>
            <p className="text-xs font-medium text-muted mb-1">Files to Edit</p>
            <div className="flex flex-wrap gap-2">
              {q.files_to_edit.map((f) => (
                <span key={f} className="rounded bg-border px-2 py-0.5 font-mono text-xs">{f}</span>
              ))}
            </div>
          </div>
        )}
        {q.notes?.length > 0 && (
          <div>
            <p className="text-xs font-medium text-muted mb-1">Notes / Hints</p>
            <ul className="list-disc pl-5 space-y-1">
              {q.notes.map((n, i) => <li key={i} className="text-muted text-xs">{n}</li>)}
            </ul>
          </div>
        )}
        {q.boilerplate_code && (
          <div>
            <div className="flex items-center justify-between mb-1">
              <p className="text-xs font-medium text-muted">Boilerplate Code</p>
              <button onClick={() => navigator.clipboard.writeText(q.boilerplate_code!)}
                className="text-xs text-primary hover:underline">Copy</button>
            </div>
            <pre className="overflow-auto rounded-lg bg-bg p-3 text-xs font-mono border border-border whitespace-pre-wrap">{q.boilerplate_code}</pre>
          </div>
        )}
      </div>

      {/* YAML view */}
      {showYaml && (
        <div className="mt-4">
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs font-medium text-muted">question.yaml</p>
            <button onClick={() => navigator.clipboard.writeText(toYaml(q))}
              className="text-xs text-primary hover:underline">Copy</button>
          </div>
          <pre className="overflow-auto rounded-lg bg-bg p-3 text-xs font-mono border border-border max-h-96 whitespace-pre-wrap">{toYaml(q)}</pre>
        </div>
      )}

      {/* Rejection reason + notes */}
      <div className="mt-4 grid grid-cols-[1fr_1fr] gap-2">
        <div>
          <label className="text-xs text-muted block mb-1">Rejection Reason</label>
          <select value={reason} onChange={(e) => onUpdateReason(q.question_id, e.target.value)}
            className="w-full rounded-lg border border-border bg-bg px-2 py-1.5 text-xs outline-none focus:border-primary">
            <option value="">— select if rejecting —</option>
            {REJECTION_REASONS.map((r) => (
              <option key={r.value} value={r.value}>{r.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs text-muted block mb-1">Notes</label>
          <textarea
            value={q.annotation.notes}
            onChange={(e) => onUpdateNotes(q.question_id, e.target.value)}
            placeholder="Optional notes…"
            rows={2}
            className="w-full rounded-lg border border-border bg-bg px-3 py-1.5 text-xs outline-none focus:border-primary resize-none"
          />
        </div>
      </div>
    </div>
  )
}

export default function ReviewTab() {
  const [runs, setRuns] = useState<RunOutputMeta[]>([])
  const [selectedRun, setSelectedRun] = useState<RunOutputMeta | null>(null)
  const [statusFilter, setStatusFilter] = useState<'approved' | 'rejected' | 'all'>('all')
  const [questions, setQuestions] = useState<EvalQuestion[]>([])
  const [rejectionReasons, setRejectionReasons] = useState<Record<string, string>>({})
  const [loadingQuestions, setLoadingQuestions] = useState(false)
  const [setMetas, setSetMetas] = useState<EvalSetMeta[]>([])
  const [currentSet, setCurrentSet] = useState<EvalSet | null>(null)
  const [setName, setSetName] = useState('')
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState<string | null>(null)
  const [insights, setInsights] = useState<{ category: string; count: number }[]>([])
  const [showInsights, setShowInsights] = useState(false)

  useEffect(() => {
    window.api?.outputs.listRuns().then((r) => setRuns(r as RunOutputMeta[])).catch(() => {})
    window.api?.review.listSets().then(setSetMetas).catch(() => {})
    window.api?.review.getInsights?.().then((ins) => setInsights(ins as { category: string; count: number }[])).catch(() => {})
  }, [])

  const flash = (msg: string) => { setToast(msg); setTimeout(() => setToast(null), 2500) }

  const loadRun = async (run: RunOutputMeta) => {
    setSelectedRun(run)
    setLoadingQuestions(true)
    setCurrentSet(null)
    try {
      const qs = await window.api.outputs.loadQuestions(run.dir, statusFilter)
      setQuestions((qs as unknown as EvalQuestion[]).map((q) => ({ ...q, annotation: { approved: null, notes: '' } })))
    } finally {
      setLoadingQuestions(false)
    }
  }

  // Reload when status filter changes
  useEffect(() => {
    if (selectedRun) {
      void loadRun(selectedRun)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter])

  const handleDecision = async (qid: string, approved: boolean, notes: string, reasonCategory: string) => {
    await window.api.review.record(qid, approved, notes, reasonCategory)
    setQuestions((prev) => prev.map((q) => q.question_id === qid ? { ...q, annotation: { approved, notes } } : q))
    flash(`${approved ? 'Approved' : 'Rejected'}: ${qid}`)
    // Refresh insights
    window.api?.review.getInsights?.().then((ins) => setInsights(ins as { category: string; count: number }[])).catch(() => {})
  }

  const handleUpdateNotes = (qid: string, notes: string) => {
    setQuestions((prev) => prev.map((q) => q.question_id === qid ? { ...q, annotation: { ...q.annotation, notes } } : q))
  }

  const handleUpdateReason = (qid: string, reason: string) => {
    setRejectionReasons((prev) => ({ ...prev, [qid]: reason }))
  }

  const saveSet = async () => {
    if (!setName.trim() || !questions.length) return
    setSaving(true)
    try {
      const set: EvalSet = { name: setName.trim(), created_at: new Date().toISOString(), questions }
      await window.api.review.saveSet(set)
      setCurrentSet(set)
      const metas = await window.api.review.listSets()
      setSetMetas(metas)
      flash(`Eval set "${setName.trim()}" saved`)
    } finally {
      setSaving(false)
    }
  }

  const loadSet = async (name: string) => {
    const set = await window.api.review.loadSet(name)
    if (set) { setCurrentSet(set); setQuestions(set.questions); setSelectedRun(null); flash(`Loaded eval set "${name}"`) }
  }

  const deleteSet = async (name: string) => {
    if (!window.confirm(`Delete eval set "${name}"?`)) return
    await window.api.review.deleteSet(name)
    const metas = await window.api.review.listSets()
    setSetMetas(metas)
    if (currentSet?.name === name) setCurrentSet(null)
    flash(`Deleted "${name}"`)
  }

  const exportSet = () => {
    if (!currentSet) return
    const blob = new Blob([JSON.stringify(currentSet, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${currentSet.name}_${currentSet.created_at.slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const annotated = questions.filter((q) => q.annotation.approved !== null).length
  const humanApproved = questions.filter((q) => q.annotation.approved === true).length
  const humanRejected = questions.filter((q) => q.annotation.approved === false).length

  return (
    <div className="flex h-full px-0 py-0">
      {/* Left panel */}
      <div className="flex w-72 shrink-0 flex-col border-r border-border bg-surface">
        <div className="border-b border-border p-4">
          <h2 className="font-semibold">Human Review</h2>
          <p className="mt-0.5 text-xs text-muted">Annotate questions · learn from rejections</p>
        </div>

        {/* Status filter */}
        <div className="border-b border-border px-3 py-2">
          <p className="mb-1.5 text-xs font-medium text-muted">Show questions</p>
          <div className="flex gap-1">
            {(['all', 'approved', 'rejected'] as const).map((s) => (
              <button key={s} onClick={() => setStatusFilter(s)}
                className={`flex-1 rounded px-2 py-1 text-xs capitalize ${statusFilter === s ? 'bg-primary text-white' : 'border border-border text-muted hover:text-text'}`}>
                {s}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-3">
          <p className="mb-2 text-xs font-medium text-muted">Runs (newest first)</p>
          {runs.length === 0 && <p className="text-xs text-muted">No runs found.</p>}
          {runs.map((run) => (
            <button key={run.run_id}
              onClick={() => loadRun(run)}
              className={`mb-1 w-full rounded-lg p-3 text-left transition-colors ${selectedRun?.run_id === run.run_id ? 'bg-primary/10 border border-primary/30' : 'hover:bg-border'}`}>
              <div className="truncate text-sm font-medium">{run.topic}</div>
              <div className="mt-0.5 flex items-center gap-2 text-xs text-muted">
                <span>{String(run.created_at ?? '').slice(0, 10)}</span>
                <span className="text-success">{run.num_approved}✓</span>
                <span className="text-danger">{run.num_rejected}✗</span>
              </div>
            </button>
          ))}
        </div>

        {/* Insights panel */}
        <div className="border-t border-border p-3">
          <button onClick={() => setShowInsights((o) => !o)} className="flex items-center justify-between w-full text-xs font-medium text-muted hover:text-text mb-2">
            <span>Rejection Insights (continuous learning)</span>
            <span>{showInsights ? '▲' : '▼'}</span>
          </button>
          {showInsights && (
            <div className="space-y-1">
              {insights.length === 0 && <p className="text-xs text-muted">No rejections recorded yet.</p>}
              {insights.map((ins) => (
                <div key={ins.category} className="flex items-center justify-between text-xs">
                  <span className="text-muted capitalize">{ins.category.replace(/_/g, ' ')}</span>
                  <span className="font-medium text-danger">{ins.count}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Eval Set management */}
        <div className="border-t border-border p-3">
          <p className="mb-2 text-xs font-medium text-muted">Eval Sets</p>
          {setMetas.length > 0 && (
            <div className="mb-2 space-y-1">
              {setMetas.map((m) => (
                <div key={m.name} className="flex items-center gap-1">
                  <button onClick={() => loadSet(m.name)} className="flex-1 truncate rounded px-2 py-1 text-left text-xs hover:bg-border">
                    {m.name} ({m.count}q, {m.annotated} ann.)
                  </button>
                  <button onClick={() => deleteSet(m.name)} className="text-xs text-danger hover:bg-danger/10 rounded px-1">✕</button>
                </div>
              ))}
            </div>
          )}
          <div className="flex gap-1">
            <input value={setName} onChange={(e) => setSetName(e.target.value)} placeholder="Set name"
              className="flex-1 rounded border border-border bg-bg px-2 py-1 text-xs outline-none focus:border-primary" />
            <button onClick={saveSet} disabled={saving || !setName.trim() || !questions.length}
              className="rounded bg-primary px-2 py-1 text-xs text-white disabled:opacity-50">
              Save
            </button>
          </div>
          {currentSet && (
            <button onClick={exportSet} className="mt-1 w-full rounded border border-border px-2 py-1 text-xs text-muted hover:text-text">
              Export "{currentSet.name}"
            </button>
          )}
        </div>
      </div>

      {/* Right panel */}
      <div className="flex-1 overflow-y-auto p-6">
        {toast && (
          <div className="mb-4 rounded-lg border border-success/30 bg-success/10 px-3 py-2 text-sm text-success">{toast}</div>
        )}

        {!selectedRun && !currentSet && (
          <div className="flex h-64 items-center justify-center text-muted">
            Select a run from the left panel to start reviewing.
          </div>
        )}

        {loadingQuestions && (
          <div className="flex h-64 items-center justify-center text-muted">Loading questions…</div>
        )}

        {!loadingQuestions && questions.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">{questions.length} questions from {selectedRun?.topic ?? currentSet?.name}</p>
                <p className="text-xs text-muted mt-0.5">
                  {annotated} annotated · <span className="text-success">{humanApproved} approved</span> · <span className="text-danger">{humanRejected} rejected</span>
                </p>
              </div>
            </div>
            {questions.map((q) => (
              <QuestionCard
                key={q.question_id}
                q={q}
                onDecision={handleDecision}
                onUpdateNotes={handleUpdateNotes}
                onUpdateReason={handleUpdateReason}
                reason={rejectionReasons[q.question_id] ?? ''}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
