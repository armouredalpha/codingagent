import {
  BarChart3,
  CheckCircle2,
  Cpu,
  Database,
  Play,
  Server,
  Settings,
  Sliders,
  type LucideIcon,
} from 'lucide-react'
import { useStore } from '../store'
import type { TabId } from '../types'

const NAV: { id: TabId; label: string; Icon: LucideIcon }[] = [
  { id: 'config', label: 'Config', Icon: Sliders },
  { id: 'dashboard', label: 'Dashboard', Icon: BarChart3 },
  { id: 'run', label: 'Run', Icon: Play },
  { id: 'questions', label: 'Questions', Icon: Database },
  { id: 'review', label: 'Review', Icon: CheckCircle2 },
  { id: 'qdrant', label: 'Qdrant', Icon: Server },
]

export default function NavRail() {
  const activeTab = useStore((s) => s.activeTab)
  const setActiveTab = useStore((s) => s.setActiveTab)

  return (
    <nav className="flex w-16 flex-col items-center border-r border-border bg-surface py-3">
      <button
        title="Home"
        onClick={() => setActiveTab(null)}
        className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg hover:bg-border"
      >
        <Cpu className="h-6 w-6 text-primary" />
      </button>

      <div className="flex flex-1 flex-col gap-1">
        {NAV.map(({ id, label, Icon }) => {
          const active = activeTab === id
          return (
            <button
              key={id}
              title={label}
              onClick={() => setActiveTab(id)}
              className={`relative flex h-12 w-12 items-center justify-center rounded-lg transition-colors ${
                active
                  ? 'bg-primary/15 text-primary'
                  : 'text-muted hover:bg-border hover:text-text'
              }`}
            >
              <Icon className="h-5 w-5" />
              {active && (
                <span className="absolute left-0 h-6 w-0.5 rounded-r bg-primary" />
              )}
            </button>
          )
        })}
      </div>

      <button
        title="Settings"
        className="mt-auto flex h-12 w-12 items-center justify-center rounded-lg text-muted hover:bg-border hover:text-text"
      >
        <Settings className="h-5 w-5" />
      </button>
    </nav>
  )
}
