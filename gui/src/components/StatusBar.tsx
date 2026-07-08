import { useStore } from '../store'

export default function StatusBar() {
  const s = useStore((st) => st.status)
  const sep = <span className="text-border">|</span>

  return (
    <footer className="flex h-8 shrink-0 items-center gap-3 border-t border-border bg-surface px-3 text-xs text-muted">
      <span className="flex items-center gap-1.5">
        <span
          className={`h-2 w-2 rounded-full ${s.connected ? 'bg-success' : 'bg-danger'}`}
        />
        {s.provider}
      </span>
      {sep}
      <span>
        generator → {s.modelRoute.generator} · supervisor → {s.modelRoute.supervisor} · judge → {s.modelRoute.judge}
      </span>
      {sep}
      <span>
        DB: {s.dbPath}
        {s.dbRows != null ? ` (${s.dbRows} rows)` : ''}
      </span>
      <span className="ml-auto font-medium text-text">
        Session cost: ${s.sessionCost.toFixed(3)}
      </span>
    </footer>
  )
}
