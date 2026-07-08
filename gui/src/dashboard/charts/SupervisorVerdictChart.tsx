import { Cell, Pie, PieChart, Tooltip } from 'recharts'
import { COLORS, TOOLTIP_STYLE } from '../palette'
import ChartCard from '../ChartCard'
import type { UsageHistoryEntry } from '../../types'

export default function SupervisorVerdictChart({ data }: { data: UsageHistoryEntry[] }) {
  const approved = data.filter((r) => r.supervisor_status === 'APPROVED').length
  const rejected = data.filter((r) => r.supervisor_status === 'REJECTED').length
  const chartData = [
    { name: 'APPROVED', value: approved },
    { name: 'REJECTED', value: rejected },
  ].filter((d) => d.value > 0)
  return (
    <ChartCard title="Supervisor Verdict" subtitle="APPROVED vs REJECTED across all runs" empty={chartData.length === 0}>
      <PieChart>
        <Pie data={chartData} cx="50%" cy="50%" innerRadius={60} outerRadius={100} dataKey="value" nameKey="name" label={(e) => { const r = e as unknown as Record<string, unknown>; return `${r.name} ${((Number(r.percent) || 0) * 100).toFixed(0)}%` }} labelLine={false}>
          <Cell fill={COLORS.success} />
          <Cell fill={COLORS.danger} />
        </Pie>
        <Tooltip {...TOOLTIP_STYLE} />
      </PieChart>
    </ChartCard>
  )
}
