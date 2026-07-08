import fs from 'node:fs'

export function lintFile(filePath: string): { path: string; word_count: number; section_count: number; status: 'PASS' | 'WARN' | 'FAIL'; message: string } {
  try {
    const text = fs.readFileSync(filePath, 'utf-8')
    const words = text.split(/\s+/).filter(Boolean).length
    const sections = (text.match(/^#+\s/gm) ?? []).length
    let status: 'PASS' | 'WARN' | 'FAIL' = 'PASS'
    let message = 'Source looks good.'
    if (words < 100) { status = 'FAIL'; message = `Only ${words} words — need at least 100.` }
    else if (words < 300) { status = 'WARN'; message = `${words} words — recommend 300+ for best results.` }
    return { path: filePath, word_count: words, section_count: sections, status, message }
  } catch (e) {
    return { path: filePath, word_count: 0, section_count: 0, status: 'FAIL', message: String(e) }
  }
}
