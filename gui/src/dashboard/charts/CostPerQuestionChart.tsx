import { CartesianGrid, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from 'recharts'
import { COLORS, TOOLTIP_STYLE } from '../palette'
import ChartCard from '../ChartCard'
import type { UsageHistoryEntry } from '../../types'

export default function CostPerQuestionChart({ data }: { data: UsageHistoryEntry[] }) {
  const chartData = data.filter((r) => r.num_questions > 0 && r.estimated_cost_usd > 0).map((r) => ({
    questions: r.num_questions,
    costPerQ: Number(r.avg_cost_per_question_usd ?? (r.estimated_cost_usd / r.num_questions)),
    topic: r.topic.slice(0, 20),
  }))
  return (
    <ChartCard title="Cost Per Question" subtitle="x = num_questions, y = avg cost/question" empty={chartData.length === 0}>
      <ScatterChart margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
        <CartesianGrid stroke={COLORS.border} />
        <XAxis dataKey="questions" stroke={COLORS.muted} fontSize={11} tickLine={false} name="Questions" />
        <YAxis dataKey="costPerQ" stroke={COLORS.muted} fontSize={11} tickLine={false} tickFormatter={(v) => `$${v.toFixed(3)}`} name="Cost/Q" />
        <Tooltip {...TOOLTIP_STYLE} cursor={{ strokeDasharray: '3 3' }} formatter={(v, name) => [name === 'costPerQ' ? `$${Number(v).toFixed(4)}` : v, name === 'costPerQ' ? 'Cost/Q' : 'Questions']} />
        <Scatter data={chartData} fill={COLORS.primary} />
      </ScatterChart>
    </ChartCard>
  )
}
