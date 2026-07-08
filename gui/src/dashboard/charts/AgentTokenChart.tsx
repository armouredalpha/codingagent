import { Bar, BarChart, CartesianGrid, Tooltip, XAxis, YAxis, Legend } from 'recharts'
import { COLORS, TOOLTIP_STYLE } from '../palette'
import ChartCard from '../ChartCard'
import type { TokenReport } from '../../types'

export default function AgentTokenChart({ data }: { data: TokenReport | null }) {
  if (!data?.by_agent) return <ChartCard title="Agent Token Usage" empty>{'No data'}</ChartCard>
  const chartData = Object.entries(data.by_agent).map(([agent, v]) => ({
    agent: agent.replace(/_/g, ' ').slice(0, 20),
    cost: Number(v.cost_usd ?? 0),
    tokens: Number(v.total ?? 0),
  })).sort((a, b) => b.cost - a.cost)
  return (
    <ChartCard title="Agent Cost Breakdown" subtitle="Cost USD per agent (latest run)" empty={chartData.length === 0}>
      <BarChart data={chartData} layout="vertical" margin={{ top: 8, right: 8, bottom: 0, left: 80 }}>
        <CartesianGrid stroke={COLORS.border} horizontal={false} />
        <XAxis type="number" stroke={COLORS.muted} fontSize={11} tickLine={false} tickFormatter={(v) => `$${v.toFixed(3)}`} />
        <YAxis type="category" dataKey="agent" stroke={COLORS.muted} fontSize={10} tickLine={false} width={80} />
        <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [`$${Number(v).toFixed(4)}`, 'Cost']} />
        <Bar dataKey="cost" fill={COLORS.primary} name="Cost USD" />
      </BarChart>
    </ChartCard>
  )
}
