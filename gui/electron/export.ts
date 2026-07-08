import type { QuestionRow, ExportOptions } from '../src/types'
// We import at runtime to avoid bundling issues
export async function buildExport(rows: QuestionRow[], opts: ExportOptions): Promise<Buffer> {
  if (opts.format === 'json') {
    return Buffer.from(JSON.stringify(rows, null, 2), 'utf-8')
  }
  if (opts.format === 'xlsx') {
    const XLSX = await import('xlsx')
    const ws = XLSX.utils.json_to_sheet(rows.map((r) => ({
      id: r.question_id, topic: r.topic, difficulty: r.difficulty,
      skill: r.skill, question: r.question,
      ...(opts.includeSolution ? {} : {}),
    })))
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, 'Questions')
    return Buffer.from(XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' }))
  }
  if (opts.format === 'docx') {
    const { Document, Paragraph, TextRun, HeadingLevel, Packer } = await import('docx')
    const sections = rows.flatMap((r, i) => [
      new Paragraph({ text: `Q${i + 1}: ${r.question_id}`, heading: HeadingLevel.HEADING_2 }),
      new Paragraph({ children: [new TextRun({ text: `Difficulty: ${r.difficulty}  |  Skill: ${r.skill}`, italics: true })] }),
      new Paragraph({ text: r.question }),
      ...(r.tasks ?? []).map((t, ti) => new Paragraph({ text: `${ti + 1}. ${t}` })),
      new Paragraph({ text: '' }),
    ])
    const doc = new Document({ sections: [{ children: sections }] })
    const buf = await Packer.toBuffer(doc)
    return Buffer.from(buf)
  }
  return Buffer.from('', 'utf-8')
}
