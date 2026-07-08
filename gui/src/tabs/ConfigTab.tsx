import { useEffect, useState, type ReactNode } from 'react'
import {
  Accordion,
  NumberField,
  SegmentedField,
  SelectField,
  SliderField,
  TextField,
  ToggleField,
} from '../model/fields'
import { deepDiff, getPath, pathModified, setPath } from '../model/paths'
import { useStore } from '../store'
import type { FullConfig } from '../types'

const PROVIDERS = [
  { value: 'openrouter', label: 'openrouter' },
  { value: 'anthropic', label: 'anthropic' },
]
const PROVIDERS_OPT = [{ value: '', label: '(global)' }, ...PROVIDERS]

const PROFILES_KEY = 'robo.profiles'
function loadProfiles(): Record<string, FullConfig> {
  try { return JSON.parse(localStorage.getItem(PROFILES_KEY) ?? '{}') } catch { return {} }
}

const KNOWN_AGENTS = [
  'question_generator', 'skill_picker', 'triage_agent', 'difficulty_agent',
  'scope_agent', 'quality_judge', 'supervisor_judge', 'eval_comparator', 'md_summary',
]

export default function ConfigTab() {
  const [staged, setStaged] = useState<FullConfig | null>(null)
  const [saved, setSaved] = useState<FullConfig | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState<string | null>(null)
  const [profiles, setProfiles] = useState<Record<string, FullConfig>>({})
  const [profileName, setProfileName] = useState('')
  const hydrate = useStore((s) => s.hydrate)

  useEffect(() => {
    setProfiles(loadProfiles())
    window.api?.config.dump()
      .then((c) => { setStaged(c); setSaved(c) })
      .catch((e) => setLoadError(e instanceof Error ? e.message : String(e)))
  }, [])

  if (loadError) {
    return (
      <div className="px-10 py-8">
        <h1 className="text-2xl font-bold">Config</h1>
        <div className="mt-6 rounded-lg border border-danger/40 bg-danger/10 p-4 text-sm text-danger">{loadError}</div>
      </div>
    )
  }
  if (!staged || !saved) {
    return <div className="px-10 py-8 text-muted">Loading config…</div>
  }

  const update = (path: string, value: unknown) =>
    setStaged((s) => (s ? setPath(s, path, value) : s))
  const mod = (path: string) => pathModified(staged, saved, path)
  const changes = deepDiff(staged, saved)
  const dirty = Object.keys(changes).length

  const flash = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(null), 2500)
  }

  const num = (path: string, label: string, o: { min?: number; max?: number; step?: number; hint?: string } = {}) => (
    <NumberField label={label} value={Number(getPath(staged, path) ?? 0)} modified={mod(path)} onChange={(v) => update(path, v)} {...o} />
  )
  const slider = (path: string, label: string, min: number, max: number, step: number, hint?: string) => (
    <SliderField label={label} value={Number(getPath(staged, path) ?? 0)} min={min} max={max} step={step} hint={hint} modified={mod(path)} onChange={(v) => update(path, v)} />
  )
  const toggle = (path: string, label: string, hint?: string) => (
    <ToggleField label={label} value={Boolean(getPath(staged, path))} hint={hint} modified={mod(path)} onChange={(v) => update(path, v)} />
  )
  const text = (path: string, label: string, ph?: string, hint?: string) => (
    <TextField label={label} value={String(getPath(staged, path) ?? '')} placeholder={ph} hint={hint} modified={mod(path)} onChange={(v) => update(path, v)} />
  )
  const seg = (path: string, label: string, opts: string[]) => (
    <SegmentedField label={label} value={String(getPath(staged, path) ?? '')} options={opts} modified={mod(path)} onChange={(v) => update(path, v)} />
  )
  const select = (path: string, label: string, opts: { value: string; label: string }[], nullable = false) => (
    <SelectField label={label} value={String(getPath(staged, path) ?? '')} options={opts} modified={mod(path)} onChange={(v) => update(path, nullable && v === '' ? null : v)} />
  )

  const onSave = async () => {
    if (!dirty) return
    setSaving(true)
    try {
      await window.api.config.write(changes)
      setSaved(staged)
      void hydrate()
      flash(`Saved ${dirty} change${dirty === 1 ? '' : 's'} to config.yaml`)
    } catch (e) {
      flash(`Save failed: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setSaving(false)
    }
  }
  const onReset = async () => {
    if (!window.confirm('Reset all fields to defaults? Your edits will be lost.')) return
    try { setStaged(await window.api.config.dump(true)) }
    catch (e) { flash(e instanceof Error ? e.message : String(e)) }
  }
  const onSaveProfile = () => {
    const name = profileName.trim()
    if (!name) return
    const next = { ...profiles, [name]: staged }
    setProfiles(next)
    localStorage.setItem(PROFILES_KEY, JSON.stringify(next))
    setProfileName('')
    flash(`Profile "${name}" saved`)
  }

  const agentModels = (staged.agent_models ?? {}) as Record<string, string>

  return (
    <div className="px-10 py-8">
      <div className="mb-2 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Config</h1>
          <p className="mt-1 text-sm text-muted">
            Every control maps to config/config.yaml. Changes are staged (yellow dot) and written only on Save.
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <button onClick={onReset} className="rounded-lg border border-border px-3 py-2 text-sm text-muted hover:text-text">
            Reset to Defaults
          </button>
          <button onClick={onSave} disabled={!dirty || saving}
            className={`rounded-lg px-4 py-2 text-sm font-semibold ${dirty && !saving ? 'bg-primary text-white hover:bg-primary/90' : 'cursor-not-allowed bg-border text-muted'}`}>
            {saving ? 'Saving…' : dirty ? `Save Config (${dirty})` : 'Saved'}
          </button>
        </div>
      </div>

      {/* Profile bar */}
      <div className="mb-6 mt-4 flex flex-wrap items-center gap-2 rounded-lg border border-border bg-surface p-3">
        <span className="text-sm text-muted">Profiles:</span>
        <select value="" onChange={(e) => { const p = profiles[e.target.value]; if (p) { setStaged(p); flash(`Profile "${e.target.value}" loaded`) } }}
          className="rounded-lg border border-border bg-bg px-3 py-1.5 text-sm">
          <option value="">Load…</option>
          {Object.keys(profiles).map((n) => <option key={n} value={n}>{n}</option>)}
        </select>
        <input value={profileName} onChange={(e) => setProfileName(e.target.value)} placeholder="profile name"
          className="rounded-lg border border-border bg-bg px-3 py-1.5 text-sm" />
        <button onClick={onSaveProfile} className="rounded-lg border border-border px-3 py-1.5 text-sm hover:border-primary">Save as profile</button>
        {toast && <span className="ml-auto text-sm text-success">{toast}</span>}
      </div>

      <div className="space-y-3">
        <Accordion title="A — Provider & Model">
          <div className="grid grid-cols-2 gap-4">
            {select('provider', 'Provider', PROVIDERS)}
            {text('model', 'Model', 'e.g. openai/gpt-4o')}
            {slider('temperature', 'Temperature', 0, 1, 0.05)}
            {num('max_tokens', 'Max Tokens', { step: 100 })}
            {text('cheap_model', 'Cheap Model', 'e.g. openai/gpt-4o-mini', 'Critic agents; falls back to model')}
            {select('cheap_provider', 'Cheap Provider', PROVIDERS_OPT, true)}
          </div>
          <div className="mt-4 border-t border-border pt-4">
            <p className="mb-2 text-sm font-medium">Per-Agent Model Overrides</p>
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
              {KNOWN_AGENTS.map((agent) => (
                <div key={agent} className="rounded-lg border border-border bg-bg p-3">
                  <div className="mb-1 text-xs text-muted">{agent.replace(/_/g, ' ')}</div>
                  <input
                    value={String(agentModels[agent] ?? '')}
                    onChange={(e) => {
                      const newAgentModels = { ...agentModels, [agent]: e.target.value }
                      update('agent_models', newAgentModels)
                    }}
                    placeholder={`(global: ${String(getPath(staged, 'model') ?? '—')})`}
                    className="w-full rounded border border-border bg-surface px-2 py-1 text-xs outline-none focus:border-primary"
                  />
                </div>
              ))}
            </div>
          </div>
        </Accordion>

        <Accordion title="B — Generation">
          <div className="grid grid-cols-2 gap-4">
            {num('num_questions', 'Questions to Generate', { min: 1, max: 60 })}
            {num('over_generation_factor', 'Over-Generation Factor', { min: 1, max: 3, step: 0.1 })}
            {num('max_regeneration_attempts', 'Max Regen Attempts', { min: 1, max: 10 })}
            {num('generation_concurrency', 'Concurrency', { min: 1, max: 16 })}
          </div>
          <div className="mt-4 border-t border-border pt-4">
            <p className="mb-3 text-sm text-muted">Difficulty Distribution</p>
            <div className="grid grid-cols-3 gap-4">
              {slider('difficulty_distribution.easy', 'Easy', 0, 1, 0.05)}
              {slider('difficulty_distribution.medium', 'Medium', 0, 1, 0.05)}
              {slider('difficulty_distribution.hard', 'Hard', 0, 1, 0.05)}
            </div>
          </div>
        </Accordion>

        <Accordion title="C — Coverage">
          <div className="grid grid-cols-2 gap-4">
            {slider('coverage_target', 'Coverage Target', 0.5, 1.0, 0.05, 'Fraction of syllabus skills that must be covered')}
            {num('max_questions', 'Max Questions', { min: 6, max: 60, hint: 'Hard cap on auto-scaling' })}
          </div>
          <div className="mt-4">{toggle('auto_scale_questions', 'Auto-Scale Questions', 'Raise num_questions toward skill count to hit coverage target')}</div>
        </Accordion>

        <Accordion title="D — Quality Gates">
          <div className="grid grid-cols-2 gap-4">
            {slider('min_confidence', 'Min Confidence', 50, 100, 1)}
            {slider('similarity_reject_threshold', 'Similarity Reject Threshold', 0.5, 1.0, 0.05)}
            {num('min_realism_score', 'Min Realism Score', { min: 0, max: 100, step: 5 })}
            {num('critic_batch_size', 'Critic Batch Size', { min: 1, max: 20 })}
          </div>
          <div className="mt-4 rounded-lg border border-border bg-bg p-4">
            <p className="mb-3 text-sm font-medium">Quality Bar</p>
            <div className="grid grid-cols-2 gap-4">
              {toggle('quality_bar.require_discriminating', 'Require Discriminating', 'Grading tests must prove starter fails')}
              {toggle('quality_bar.require_judge_approve', 'Require Judge Approve', 'LLM quality judge must not reject')}
              {toggle('quality_bar.require_in_scope', 'Require In-Scope')}
              {slider('quality_bar.max_similarity', 'Max Similarity', 0.5, 1.0, 0.05)}
              {slider('quality_bar.min_difficulty_fit', 'Min Difficulty Fit', 0, 1, 0.05)}
            </div>
          </div>
        </Accordion>

        <Accordion title="E — Grading Backend">
          <div className="grid grid-cols-2 gap-4">
            {seg('grading_backend', 'Grading Backend', ['ast', 'docker'])}
            {text('sandbox_image', 'Sandbox Image')}
            {num('sandbox_timeout_s', 'Timeout (s)')}
            {num('sandbox_warmup_s', 'Warmup (s)', { step: 0.5 })}
            {text('sandbox_cpus', 'CPUs')}
            {text('sandbox_memory', 'Memory')}
            {num('sandbox_pids_limit', 'PIDs Limit')}
          </div>
        </Accordion>

        <Accordion title="F — Human Review">
          <div className="grid grid-cols-2 gap-4">
            {toggle('human_review_enabled', 'Enable Human Review')}
            {seg('human_review_mode', 'Review Mode', ['log', 'defer', 'block'])}
            {slider('human_review_confidence_min', 'Confidence Min', 70, 90, 1)}
            {slider('human_review_confidence_max', 'Confidence Max', 70, 90, 1)}
          </div>
        </Accordion>

        <Accordion title="G — Autonomy">
          {num('max_planner_steps', 'Max Planner Steps', { min: 1, max: 20 })}
        </Accordion>

        <Accordion title="H — Pricing (USD / 1M tokens)">
          <div className="grid grid-cols-2 gap-4">
            {num('pricing.input_per_million_tokens', 'Input / 1M', { min: 0, step: 0.01 })}
            {num('pricing.output_per_million_tokens', 'Output / 1M', { min: 0, step: 0.01 })}
          </div>
        </Accordion>
      </div>
    </div>
  )
}
