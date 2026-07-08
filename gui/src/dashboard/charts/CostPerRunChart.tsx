import { CartesianGrid, Line, LineChart, Tooltip, XAxis, YAxis } from 'recharts'
import { COLORS, TOOLTIP_STYLE } from '../palette'
import ChartCard from '../ChartCard'
import type { UsageHistoryEntry } from '../../types'

export default function CostPerRunChart({ data }: { data: UsageHistoryEntry[] }) {
  const chartData = data.slice(0, 15).reverse().map((r, i) => ({
    name: String(i + 1),
    cost: Number(r.estimated_cost_usd ?? 0),
    topic: r.topic.slice(0, 20),
  }))
  return (
    <ChartCard title="Cost Per Run" subtitle="Estimated cost USD · last 15 runs" empty={chartData.length === 0}>
      <LineChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
        <CartesianGrid stroke={COLORS.border} vertical={false} />
        <XAxis dataKey="name" stroke={COLORS.muted} fontSize={11} tickLine={false} />
        <YAxis stroke={COLORS.muted} fontSize={11} tickLine={false} tickFormatter={(v) => `$${v.toFixed(2)}`} />
        <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [`$${Number(v).toFixed(3)}`, 'Cost']} />
        <Line type="monotone" dataKey="cost" stroke={COLORS.warning} strokeWidth={2} dot={{ fill: COLORS.warning, r: 3 }} />
      </LineChart>
    </ChartCard>
  )
}
