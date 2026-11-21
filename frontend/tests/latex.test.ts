import { describe, expect, it } from 'vitest'
import { wrapBareLatex } from '../src/utils/latex'

describe('wrapBareLatex', () => {
  it('wraps bare commands and superscripts', () => {
    expect(wrapBareLatex(String.raw`\bar{x}=6，s^2=2`)).toBe(
      String.raw`$\bar{x}=6$，$s^2=2$`,
    )
  })

  it('wraps a bare command inside prose', () => {
    expect(wrapBareLatex(String.raw`样本均值=\frac{7+6+5+8+4}{5}=6`)).toBe(
      String.raw`样本均值=$\frac{7+6+5+8+4}{5}=6$`,
    )
  })

  it('does not touch math that already has delimiters', () => {
    const source = String.raw`求 $\frac{X}{\sqrt{Y/5}}$ 的值`
    expect(wrapBareLatex(source)).toBe(source)
  })

  it('converts plain sqrt notation', () => {
    expect(wrapBareLatex('2sqrt(5)')).toBe(String.raw`$2\sqrt{5}$`)
  })
})
