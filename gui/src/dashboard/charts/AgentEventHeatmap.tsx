import { COLORS } from '../palette'

interface HeatmapEntry { agent: string; status: string; count: number }

export default function AgentEventHeatmap({ data }: { data: HeatmapEntry[] }) {
  const agents = [...new Set(data.map((d) => d.agent))].sort()
  const statuses = ['ok', 'warn', 'fail']
  const get = (agent: string, status: string) =>
    data.find((d) => d.agent === agent && d.status === status)?.count ?? 0
  const maxVal = Math.max(...data.map((d) => d.count), 1)

  const statusColor = { ok: COLORS.success, warn: COLORS.warning, fail: COLORS.danger }

  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <h3 className="mb-3 text-sm font-semibold">Agent Event Heatmap</h3>
      {agents.length === 0 ? (
        <div className="flex h-32 items-center justify-center text-sm text-muted">No events data yet.</div>
      ) : (
        <div className="overflow-auto">
          <table className="w-full text-xs">
            <thead>
              <tr>
                <th className="py-2 pr-4 text-left text-muted">Agent</th>
                {statuses.map((s) => (
                  <th key={s} className="px-3 py-2 text-center capitalize" style={{ color: statusColor[s as keyof typeof statusColor] }}>{s}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {agents.map((agent) => (
                <tr key={agent} className="border-t border-border/50">
                  <td className="py-1.5 pr-4 font-mono">{agent}</td>
                  {statuses.map((s) => {
                    const count = get(agent, s)
                    const intensity = count / maxVal
                    return (
                      <td key={s} className="px-3 py-1.5 text-center">
                        {count > 0 ? (
                          <span className="rounded px-2 py-0.5 font-medium"
                            style={{ background: `${statusColor[s as keyof typeof statusColor]}${Math.round(intensity * 80 + 20).toString(16)}`, color: statusColor[s as keyof typeof statusColor] }}>
                            {count}
                          </span>
                        ) : (
                          <span className="text-muted">—</span>
                        )}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
