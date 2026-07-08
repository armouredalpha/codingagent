import { useEffect, useState } from 'react'
import SourceDropZone, { type SelectedFile } from '../components/SourceDropZone'
import SourceQualityCard from '../components/SourceQualityCard'
import RunConfigPanel, { type RunConfig } from '../components/RunConfigPanel'
import RunExecution from '../components/RunExecution'
import { useStore } from '../store'
import type { LintReport } from '../types'
import type { RunStartParams } from '../api'

export default function RunTab() {
  const run = useStore((s) => s.run)
  const resetRun = useStore((s) => s.resetRun)

  const [file, setFile] = useState<SelectedFile | null>(null)
  const [linting, setLinting] = useState(false)
  const [report, setReport] = useState<LintReport | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [runParams, setRunParams] = useState<RunStartParams | null>(null)
  const [config, setConfig] = useState<RunConfig>({
    numQuestions: 6,
    maxLoops: 3,
    diffEasy: 0.30,
    diffMedium: 0.50,
    diffHard: 0.20,
    skipPrompts: true,
    humanReview: false,
  })

  useEffect(() => {
    window.api?.config.get().then((cfg) => {
      if (!cfg) return
    })
  }, [])

  const onSelect = async (f: SelectedFile) => {
    setError(null)
    setReport(null)
    setFile(f)
    setLinting(true)
    try {
      setReport(await window.api.lint.run(f.path))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLinting(false)
    }
  }

  const diffSum = config.diffEasy + config.diffMedium + config.diffHard
  const diffOk = Math.abs(diffSum - 1.0) <= 0.01
  const canGenerate = !!file && !!report && report.status !== 'FAIL' && diffOk

  const estimate = report && diffOk ? (() => {
    const words = report.word_count
    const candidates = config.numQuestions * 1.5
    const estIn = words * 1.3 + candidates * 380
    const estOut = candidates * 250
    return { tokens: estIn + estOut, cost: (estIn * 0.15 + estOut * 0.6) / 1_000_000 }
  })() : null

  const onGenerate = () => {
    if (!file || !canGenerate) return
    setRunParams({
      mdPath: file.path,
      maxLoops: config.maxLoops,
      numQuestions: config.numQuestions,
      diffEasy: config.diffEasy,
      diffMedium: config.diffMedium,
      diffHard: config.diffHard,
      skipPrompts: config.skipPrompts,
      humanReview: config.humanReview,
    })
  }

  const handleReset = () => {
    setRunParams(null)
    resetRun()
  }

  // If a run is active in the store (user switched tabs and came back), show execution view
  if (runParams || run.active) {
    return (
      <RunExecution
        params={runParams ?? {
          mdPath: '',
          maxLoops: 3,
          numQuestions: 6,
          diffEasy: 0.30,
          diffMedium: 0.50,
          diffHard: 0.20,
          skipPrompts: true,
          humanReview: false,
        }}
        onReset={handleReset}
      />
    )
  }

  return (
    <div className="px-10 py-8">
      <h1 className="text-2xl font-bold">Run</h1>
      <p className="mt-1 text-sm text-muted">
        Upload a .md or .docx teaching material, review the quality check, configure, and launch.
      </p>

      <div className="mt-8 grid grid-cols-[1fr_360px] gap-6">
        <div className="space-y-4">
          <SourceDropZone file={file} linting={linting} onSelect={onSelect} onError={setError} />
          {error && (
            <div className="rounded-lg border border-danger/40 bg-danger/10 p-3 text-sm text-danger">{error}</div>
          )}
          {report && <SourceQualityCard report={report} />}
        </div>

        <RunConfigPanel
          config={config}
          onChange={(p) => setConfig((c) => ({ ...c, ...p }))}
          estimate={estimate}
          canGenerate={canGenerate}
          onGenerate={onGenerate}
        />
      </div>
    </div>
  )
}
