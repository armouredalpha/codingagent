import { Bar, BarChart, CartesianGrid, Cell, Tooltip, XAxis, YAxis } from 'recharts'
import { COLORS, TOOLTIP_STYLE } from '../palette'
import ChartCard from '../ChartCard'
import type { UsageHistoryEntry } from '../../types'

export default function ApprovalByTopicChart({ data }: { data: UsageHistoryEntry[] }) {
  const byTopic = new Map<string, { approved: number; total: number }>()
  data.forEach((r) => {
    const t = r.topic.slice(0, 22)
    const prev = byTopic.get(t) ?? { approved: 0, total: 0 }
    byTopic.set(t, { approved: prev.approved + (r.num_approved ?? 0), total: prev.total + (r.num_questions ?? 0) })
  })
  const chartData = [...byTopic.entries()]
    .map(([topic, v]) => ({ topic, rate: v.total ? (v.approved / v.total) * 100 : 0 }))
    .sort((a, b) => b.rate - a.rate)
  return (
    <ChartCard title="Approval Rate by Topic" subtitle="% approved per topic" height={Math.max(200, chartData.length * 36)} empty={chartData.length === 0}>
      <BarChart data={chartData} layout="vertical" margin={{ top: 8, right: 24, bottom: 0, left: 100 }}>
        <CartesianGrid stroke={COLORS.border} horizontal={false} />
        <XAxis type="number" domain={[0, 100]} stroke={COLORS.muted} fontSize={11} tickLine={false} tickFormatter={(v) => `${v}%`} />
        <YAxis type="category" dataKey="topic" stroke={COLORS.muted} fontSize={10} tickLine={false} width={100} />
        <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [`${Number(v).toFixed(1)}%`, 'Approval rate']} />
        <Bar dataKey="rate" name="Approval %">
          {chartData.map((entry) => (
            <Cell key={entry.topic} fill={entry.rate >= 70 ? COLORS.success : entry.rate >= 40 ? COLORS.warning : COLORS.danger} />
          ))}
        </Bar>
      </BarChart>
    </ChartCard>
  )
}
