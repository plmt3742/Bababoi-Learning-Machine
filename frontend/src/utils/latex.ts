const BARE_LATEX =
  /(?:\\[a-zA-Z]+(?:\s*(?:\[[^\]]*\])?(?:\{[^{}]*\})*)(?:\s*[\^_]\s*(?:\{[^{}]*\}|[^\s，。；,;、]+))?(?:\s*[=<>]\s*[^\s，。；,;、]+)?|(?<![\w$])[A-Za-z][\^_]\s*(?:\{[^{}]*\}|[0-9]+)(?:\s*[=<>]\s*[^\s，。；,;、]+)?)/g

const PLAIN_SQRT = /(?<![\\\w])(\d*)sqrt\(([^()]*)\)/g

export function findClosingDelimiter(
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

function wrapChunk(chunk: string): string {
  const withLatex = chunk.replace(BARE_LATEX, (match) => `$${match}$`)
  return withLatex.replace(
    PLAIN_SQRT,
    (_match, coefficient: string, body: string) => `$${coefficient}\\sqrt{${body}}$`,
  )
}

export function wrapBareLatex(source: string): string {
  let result = ''
  let cursor = 0
  let index = 0

  while (index < source.length) {
    if (source[index] !== '$') {
      index += 1
      continue
    }

    const display = source[index + 1] === '$'
    const delimiter = display ? '$$' : '$'
    const closing = findClosingDelimiter(source, index + delimiter.length, delimiter, display)
    if (closing === -1) {
      index += 1
      continue
    }

    result += wrapChunk(source.slice(cursor, index))
    result += source.slice(index, closing + delimiter.length)
    index = closing + delimiter.length
    cursor = index
  }

  return result + wrapChunk(source.slice(cursor))
}
