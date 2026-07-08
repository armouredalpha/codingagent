import { Cell, Pie, PieChart, Tooltip, Legend } from 'recharts'
import { COLORS, DIFFICULTY_COLOR, TOOLTIP_STYLE } from '../palette'
import ChartCard from '../ChartCard'

export default function DifficultyDistributionChart({ data }: { data: { difficulty: string; count: number }[] }) {
  return (
    <ChartCard title="Difficulty Distribution" subtitle="Easy / Medium / Hard across approved questions" empty={data.length === 0}>
      <PieChart>
        <Pie data={data} cx="50%" cy="50%" outerRadius={100} dataKey="count" nameKey="difficulty" label={(e) => { const r = e as unknown as Record<string, unknown>; return `${r.difficulty ?? r.name} ${((Number(r.percent) || 0) * 100).toFixed(0)}%` }} labelLine={false}>
          {data.map((entry) => (
            <Cell key={entry.difficulty} fill={DIFFICULTY_COLOR[entry.difficulty] ?? COLORS.muted} />
          ))}
        </Pie>
        <Tooltip {...TOOLTIP_STYLE} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
      </PieChart>
    </ChartCard>
  )
}
