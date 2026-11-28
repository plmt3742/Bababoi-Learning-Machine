export type MarkdownSegment =
  | { type: 'markdown'; content: string }
  | { type: 'mermaid'; source: string }

const FENCE_OPEN = /^[ \t]{0,3}```([^\s`]*)[ \t]*$/
const FENCE_CLOSE = /^[ \t]{0,3}```[ \t]*$/

function findClosingFence(lines: string[], start: number): number {
  for (let index = start + 1; index < lines.length; index += 1) {
    if (FENCE_CLOSE.test(lines[index])) return index
  }
  return -1
}

/** Split markdown into plain segments and standalone ```mermaid fences. */
export function splitMermaidFences(source: string): MarkdownSegment[] {
  if (!source.trim()) return []

  const lines = source.split(/\r?\n/)
  const segments: MarkdownSegment[] = []
  let markdownLines: string[] = []

  const flushMarkdown = (): void => {
    const content = markdownLines.join('\n')
    markdownLines = []
    if (content.trim()) segments.push({ type: 'markdown', content })
  }

  for (let index = 0; index < lines.length; index += 1) {
    const open = FENCE_OPEN.exec(lines[index])
    if (!open) {
      markdownLines.push(lines[index])
      continue
    }

    const closing = findClosingFence(lines, index)
    if (closing === -1) {
      markdownLines.push(lines[index])
      continue
    }

    if (open[1].toLowerCase() !== 'mermaid') {
      markdownLines.push(...lines.slice(index, closing + 1))
      index = closing
      continue
    }

    const diagram = lines.slice(index + 1, closing).join('\n').trim()
    if (!diagram) {
      markdownLines.push(...lines.slice(index, closing + 1))
    } else {
      flushMarkdown()
      segments.push({ type: 'mermaid', source: diagram })
    }
    index = closing
  }

  flushMarkdown()
  return segments
}
