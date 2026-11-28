import { describe, expect, it } from 'vitest'
import { splitMermaidFences } from '../src/utils/mermaid'

describe('splitMermaidFences', () => {
  it('returns one markdown segment when there is no mermaid fence', () => {
    const source = '普通文本\n\n```js\nconst answer = 42\n```'
    expect(splitMermaidFences(source)).toEqual([{ type: 'markdown', content: source }])
  })

  it('splits text around standalone mermaid fences', () => {
    const source = '前文\n\n```mermaid\nflowchart LR\nA --> B\n```\n\n后文'
    expect(splitMermaidFences(source)).toEqual([
      { type: 'markdown', content: '前文\n' },
      { type: 'mermaid', source: 'flowchart LR\nA --> B' },
      { type: 'markdown', content: '\n后文' },
    ])
  })

  it('handles CRLF and uppercase fences, and keeps unclosed fences as markdown', () => {
    expect(splitMermaidFences('A\r\n```MERMAID\r\nflowchart TD\r\nX-->Y\r\n```')).toEqual([
      { type: 'markdown', content: 'A' },
      { type: 'mermaid', source: 'flowchart TD\nX-->Y' },
    ])

    const unclosed = '```mermaid\nflowchart LR\nA --> B'
    expect(splitMermaidFences(unclosed)).toEqual([{ type: 'markdown', content: unclosed }])
  })
})
