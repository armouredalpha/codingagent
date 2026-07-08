import { Bar, BarChart, CartesianGrid, Legend, Tooltip, XAxis, YAxis } from 'recharts'
import { COLORS, TOOLTIP_STYLE } from '../palette'
import ChartCard from '../ChartCard'
import type { UsageHistoryEntry } from '../../types'

export default function QuestionsPerRunChart({ data }: { data: UsageHistoryEntry[] }) {
  const chartData = data.slice(0, 15).reverse().map((r) => ({
    name: `${r.topic.slice(0, 18)}${r.loop_num ? ` L${r.loop_num}` : ''}`,
    approved: r.num_approved,
    rejected: (r.num_questions ?? 0) - (r.num_approved ?? 0),
    run_id: r.run_id,
  }))
  return (
    <ChartCard title="Questions Per Run" subtitle={`Approved vs rejected · last ${chartData.length} runs`} empty={chartData.length === 0}>
      <BarChart data={chartData} margin={{ top: 8, right: 8, bottom: 24, left: -16 }}>
        <CartesianGrid stroke={COLORS.border} vertical={false} />
        <XAxis dataKey="name" stroke={COLORS.muted} fontSize={10} tickLine={false} angle={-20} textAnchor="end" />
        <YAxis stroke={COLORS.muted} fontSize={11} tickLine={false} allowDecimals={false} />
        <Tooltip {...TOOLTIP_STYLE} cursor={{ fill: COLORS.border, opacity: 0.3 }} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="approved" stackId="q" fill={COLORS.success} name="Approved" />
        <Bar dataKey="rejected" stackId="q" fill={COLORS.danger} name="Rejected" />
      </BarChart>
    </ChartCard>
  )
}
