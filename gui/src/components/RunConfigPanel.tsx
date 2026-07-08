export interface RunConfig {
  numQuestions: number
  maxLoops: number
  diffEasy: number
  diffMedium: number
  diffHard: number
  skipPrompts: boolean
  humanReview: boolean
}

interface Props {
  config: RunConfig
  onChange: (patch: Partial<RunConfig>) => void
  estimate: { cost: number; tokens: number } | null
  canGenerate: boolean
  onGenerate: () => void
}

function DiffSlider({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <div>
      <div className="flex justify-between text-sm">
        <span className="text-muted">{label}</span>
        <span>{(value * 100).toFixed(0)}%</span>
      </div>
      <input type="range" min={0} max={1} step={0.05} value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-1 w-full accent-primary" />
    </div>
  )
}

export default function RunConfigPanel({ config, onChange, estimate, canGenerate, onGenerate }: Props) {
  const diffSum = config.diffEasy + config.diffMedium + config.diffHard
  const diffWarn = Math.abs(diffSum - 1.0) > 0.01

  return (
    <div className="rounded-xl border border-border bg-surface p-5">
      <h3 className="mb-4 font-semibold">Run Configuration</h3>

      <label className="block text-sm text-muted">Questions to Generate</label>
      <input type="number" min={1} max={60} value={config.numQuestions}
        onChange={(e) => onChange({ numQuestions: Math.max(1, Math.min(60, Number(e.target.value) || 1)) })}
        className="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm outline-none focus:border-primary" />

      <label className="mt-4 block text-sm text-muted">Max Loops</label>
      <input type="number" min={1} max={5} value={config.maxLoops}
        onChange={(e) => onChange({ maxLoops: Math.max(1, Math.min(5, Number(e.target.value) || 1)) })}
        className="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm outline-none focus:border-primary" />

      <p className="mt-4 text-sm text-muted">Difficulty Distribution</p>
      {diffWarn && (
        <p className="mt-1 rounded border border-warning/30 bg-warning/10 px-2 py-1 text-xs text-warning">
          Easy + Medium + Hard must sum to 100% (currently {(diffSum * 100).toFixed(0)}%)
        </p>
      )}
      <div className="mt-2 space-y-3">
        <DiffSlider label="Easy" value={config.diffEasy} onChange={(v) => onChange({ diffEasy: v })} />
        <DiffSlider label="Medium" value={config.diffMedium} onChange={(v) => onChange({ diffMedium: v })} />
        <DiffSlider label="Hard" value={config.diffHard} onChange={(v) => onChange({ diffHard: v })} />
      </div>

      <div className="mt-4 flex flex-col gap-2">
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={config.skipPrompts}
            onChange={(e) => onChange({ skipPrompts: e.target.checked })}
            className="rounded accent-primary" />
          <span>Skip prompts (--yes)</span>
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={config.humanReview}
            onChange={(e) => onChange({ humanReview: e.target.checked })}
            className="rounded accent-primary" />
          <span>Enable human review</span>
        </label>
      </div>

      <div className="mt-5 rounded-lg border border-border bg-bg p-3 text-sm">
        <p className="text-muted">Pre-flight estimate <span className="text-xs">(heuristic)</span></p>
        <p className="mt-1 font-medium">
          {estimate ? `~$${estimate.cost.toFixed(3)} · ~${Math.round(estimate.tokens / 1000)}k tokens` : '—'}
        </p>
      </div>

      <button
        disabled={!canGenerate || diffWarn}
        onClick={onGenerate}
        className={`mt-5 w-full rounded-lg px-4 py-3 font-semibold transition-colors ${
          canGenerate && !diffWarn
            ? 'bg-primary text-white hover:bg-primary/90'
            : 'cursor-not-allowed bg-border text-muted'
        }`}
      >
        Generate {config.numQuestions} Question{config.numQuestions !== 1 ? 's' : ''}
      </button>
    </div>
  )
}
