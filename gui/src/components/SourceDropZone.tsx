import { useCallback, useState, type DragEvent } from 'react'
import { FileText, Loader2, Upload } from 'lucide-react'

export interface SelectedFile {
  path: string
  name: string
  size: number
}

interface Props {
  file: SelectedFile | null
  linting: boolean
  onSelect: (file: SelectedFile) => void
  onError: (msg: string) => void
}

const MAX_BYTES = 10 * 1024 * 1024

// Accepts .md and .docx files (CLI converts .docx internally)
export default function SourceDropZone({ file, linting, onSelect, onError }: Props) {
  const [dragging, setDragging] = useState(false)

  const accept = useCallback(
    (filePath: string, name: string, size: number) => {
      if (!/\.(md|markdown|docx)$/i.test(name)) {
        onError('Only .md, .markdown, or .docx files are supported.')
        return
      }
      if (size > MAX_BYTES && size > 0) {
        onError('File exceeds the 10 MB limit.')
        return
      }
      onSelect({ path: filePath, name, size })
    },
    [onSelect, onError],
  )

  const onDrop = (e: DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files?.[0]
    if (!f) return
    accept(window.api.getPathForFile(f), f.name, f.size)
  }

  const browse = async () => {
    const filePath = await window.api.file.openFileDialog([
      { name: 'Teaching Materials', extensions: ['md', 'markdown', 'docx'] },
    ])
    if (!filePath) return
    const name = filePath.split(/[\\/]/).pop() ?? filePath
    accept(filePath, name, 0)
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      className={`rounded-xl border-2 border-dashed p-8 text-center transition-colors ${
        dragging ? 'border-primary bg-primary/5' : 'border-border bg-surface/50'
      }`}
    >
      {linting ? (
        <div className="flex flex-col items-center gap-2 text-muted">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p>Checking source quality…</p>
        </div>
      ) : file ? (
        <div className="flex flex-col items-center gap-2">
          <FileText className="h-8 w-8 text-primary" />
          <p className="font-medium">{file.name}</p>
          {file.size > 0 && (
            <p className="text-sm text-muted">{(file.size / 1024).toFixed(0)} KB</p>
          )}
          <button onClick={browse} className="mt-1 text-sm text-primary hover:underline">
            Choose a different file
          </button>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-3">
          <Upload className="h-8 w-8 text-muted" />
          <p className="text-muted">
            Drop a <span className="text-text">.md</span> or <span className="text-text">.docx</span> teaching material here
          </p>
          <button
            onClick={browse}
            className="rounded-lg border border-border px-4 py-2 text-sm hover:border-primary"
          >
            Browse…
          </button>
          <p className="text-xs text-muted">
            Max 10 MB · a free quality check runs on drop (no API cost)
          </p>
        </div>
      )}
    </div>
  )
}
