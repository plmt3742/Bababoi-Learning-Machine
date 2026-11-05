/**
 * Markdown + KaTeX pipeline (FE-010).
 *
 * Order matters: extract math before markdown parsing so `$...$` never gets
 * mangled by emphasis/link rules, then render markdown with raw HTML disabled,
 * inject KaTeX output, and sanitize the final HTML with DOMPurify.
 */
import DOMPurify from 'dompurify'
import katex from 'katex'
import MarkdownIt from 'markdown-it'

interface MathItem {
  placeholder: string
  tex: string
  display: boolean
}

interface ExtractedMarkdown {
  text: string
  math: MathItem[]
}

const MATH_PLACEHOLDER_PREFIX = 'BABABOIMATHPLACEHOLDER'

const markdown = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  typographer: false,
})

markdown.renderer.rules.link_open = (tokens, index, options, _env, self) => {
  const token = tokens[index]
  const href = token.attrGet('href')

  if (typeof href === 'string' && /^https?:\/\//i.test(href)) {
    token.attrSet('target', '_blank')
    token.attrSet('rel', 'noopener noreferrer')
  }

  return self.renderToken(tokens, index, options)
}

DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName !== 'A') return

  node.setAttribute('rel', 'noopener noreferrer')
  if (node.getAttribute('href')?.startsWith('http')) {
    node.setAttribute('target', '_blank')
  }
})

function escapeHtml(value: string): string {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function findClosingDelimiter(
  source: string,
  start: number,
  delimiter: string,
  display: boolean,
): number {
  let index = start

  while (index < source.length) {
    if (source[index] === '\\') {
      index += 2
      continue
    }

    if (source.startsWith(delimiter, index)) {
      // A `$` delimiter can never close on the first half of a `$$` pair.
      if (!display && source[index + 1] === '$') {
        index += 2
        continue
      }
      return index
    }

    index += 1
  }

  return -1
}

function extractMath(source: string): ExtractedMarkdown {
  let text = ''
  const math: MathItem[] = []
  let index = 0

  while (index < source.length) {
    const char = source[index]

    if (char === '\\') {
      text += source.slice(index, index + 2)
      index += 2
      continue
    }

    if (char !== '$') {
      text += char
      index += 1
      continue
    }

    const display = source[index + 1] === '$'
    const delimiter = display ? '$$' : '$'
    const contentStart = index + delimiter.length
    const closingIndex = findClosingDelimiter(source, contentStart, delimiter, display)

    if (closingIndex === -1) {
      text += char
      index += 1
      continue
    }

    const tex = source.slice(contentStart, closingIndex).trim()
    const isInlineMultiline = !display && /[\r\n]/.test(tex)

    if (!tex || isInlineMultiline) {
      text += char
      index += 1
      continue
    }

    const placeholder = `${MATH_PLACEHOLDER_PREFIX}${math.length}`
    math.push({ placeholder, tex, display })
    text += display ? `\n\n${placeholder}\n\n` : placeholder
    index = closingIndex + delimiter.length
  }

  return { text, math }
}

function renderTex(tex: string, displayMode: boolean): string {
  try {
    return katex.renderToString(tex, {
      displayMode,
      throwOnError: false,
      strict: 'ignore',
      trust: false,
      output: 'htmlAndMathml',
      errorColor: 'var(--color-danger)',
    })
  } catch {
    // KaTeX with throwOnError=false normally never throws; this is belt and
    // braces so a rendering bug can still show the readable source.
    return `<code class="md-math-fallback">${escapeHtml(tex)}</code>`
  }
}

function injectMath(html: string, math: MathItem[]): string {
  let result = html

  for (const item of math) {
    const rendered = renderTex(item.tex, item.display)

    if (!item.display) {
      result = result
        .split(item.placeholder)
        .join(`<span class="md-math-inline">${rendered}</span>`)
      continue
    }

    const blockHtml = `<div class="md-math-block">${rendered}</div>`
    const paragraphPattern = new RegExp(`<p>\\s*${item.placeholder}\\s*</p>`)

    if (paragraphPattern.test(result)) {
      result = result.replace(paragraphPattern, blockHtml)
    } else {
      result = result
        .split(item.placeholder)
        .join(`<span class="md-math-inline md-math-display">${rendered}</span>`)
    }
  }

  return result
}

export function renderMarkdown(source: string): string {
  if (!source.trim()) return ''

  const { text, math } = extractMath(source)
  const html = injectMath(markdown.render(text), math)

  return DOMPurify.sanitize(html, {
    USE_PROFILES: { html: true, mathMl: true },
    ADD_ATTR: ['target', 'rel'],
  })
}
