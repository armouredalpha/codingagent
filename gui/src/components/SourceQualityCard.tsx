import type { LintReport } from '../types'

const STATUS_COLOR = {
  PASS: 'text-success border-success/30 bg-success/5',
  WARN: 'text-warning border-warning/30 bg-warning/5',
  FAIL: 'text-danger border-danger/30 bg-danger/5',
}

export default function SourceQualityCard({ report }: { report: LintReport }) {
  const color = STATUS_COLOR[report.status]
  return (
    <div className={`rounded-xl border p-4 ${color}`}>
      <div className="flex items-center justify-between">
        <p className="font-semibold">{report.status}</p>
        <div className="flex gap-4 text-sm">
          <span>{report.word_count} words</span>
          <span>{report.section_count} sections</span>
        </div>
      </div>
      <p className="mt-1 text-sm opacity-80">{report.message}</p>
    </div>
  )
}
