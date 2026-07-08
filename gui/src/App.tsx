import { useEffect, type FC } from 'react'
import NavRail from './components/NavRail'
import StatusBar from './components/StatusBar'
import HomeBanner from './components/HomeBanner'
import { useStore } from './store'
import type { TabId } from './types'
import ConfigTab from './tabs/ConfigTab'
import DashboardTab from './tabs/DashboardTab'
import RunTab from './tabs/RunTab'
import QuestionsTab from './tabs/QuestionsTab'
import ReviewTab from './tabs/ReviewTab'
import QdrantTab from './tabs/QdrantTab'

const TABS: Record<TabId, FC> = {
  config: ConfigTab,
  dashboard: DashboardTab,
  run: RunTab,
  questions: QuestionsTab,
  review: ReviewTab,
  qdrant: QdrantTab,
}

export default function App() {
  const activeTab = useStore((s) => s.activeTab)
  const hydrate = useStore((s) => s.hydrate)
  const ActiveComponent: FC = activeTab ? TABS[activeTab] : HomeBanner

  useEffect(() => {
    void hydrate()
  }, [hydrate])

  return (
    <div className="flex h-full w-full flex-col bg-bg text-text">
      <div className="flex min-h-0 flex-1">
        <NavRail />
        <main className="min-w-0 flex-1 overflow-y-auto">
          <ActiveComponent />
        </main>
      </div>
      <StatusBar />
    </div>
  )
}
