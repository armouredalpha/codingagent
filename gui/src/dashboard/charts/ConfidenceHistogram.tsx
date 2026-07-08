import { Bar, BarChart, CartesianGrid, Tooltip, XAxis, YAxis } from 'recharts'
import { COLORS, TOOLTIP_STYLE } from '../palette'
import ChartCard from '../ChartCard'
import type { ConfidenceReport } from '../../types'

export default function ConfidenceHistogram({ data }: { data: ConfidenceReport[] }) {
  const buckets: Record<string, number> = { '0-20': 0, '20-40': 0, '40-60': 0, '60-80': 0, '80-100': 0 }
  data.forEach((report) => {
    report.questions?.forEach((q) => {
      const c = Number(q.confidence ?? 0)
      if (c < 20) buckets['0-20']++
      else if (c < 40) buckets['20-40']++
      else if (c < 60) buckets['40-60']++
      else if (c < 80) buckets['60-80']++
      else buckets['80-100']++
    })
  })
  const chartData = Object.entries(buckets).map(([range, count]) => ({ range, count }))
  const total = chartData.reduce((s, d) => s + d.count, 0)
  return (
    <ChartCard title="Confidence Distribution" subtitle="Question confidence score buckets" empty={total === 0}>
      <BarChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
        <CartesianGrid stroke={COLORS.border} vertical={false} />
        <XAxis dataKey="range" stroke={COLORS.muted} fontSize={11} tickLine={false} />
        <YAxis stroke={COLORS.muted} fontSize={11} tickLine={false} allowDecimals={false} />
        <Tooltip {...TOOLTIP_STYLE} />
        <Bar dataKey="count" fill={COLORS.primary} name="Count" />
      </BarChart>
    </ChartCard>
  )
}
