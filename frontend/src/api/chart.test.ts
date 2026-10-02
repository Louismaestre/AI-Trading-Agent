import { expect, test } from 'vitest'

import { barsToCandles, lastDayChange, walkForwardRange } from './chart'
import type { Bar } from './types'

function bar(date: string, close: string, open = close): Bar {
  return { date, open, high: close, low: open, close, volume: 1 }
}

test('barsToCandles converts decimal strings into numbers', () => {
  const candles = barsToCandles([bar('2026-09-01', '610.2500', '600.1000')])

  expect(candles).toEqual([
    { time: '2026-09-01', open: 600.1, high: 610.25, low: 600.1, close: 610.25 },
  ])
})

test('lastDayChange uses the two latest closes', () => {
  const change = lastDayChange([bar('2026-09-01', '100'), bar('2026-09-02', '110')])

  expect(change).toEqual({ close: 110, change: 10, percent: 10 })
})

test('lastDayChange is null when there is no bar', () => {
  expect(lastDayChange([])).toBeNull()
})

test('walkForwardRange uses the previous calendar year as context', () => {
  const range = walkForwardRange(new Date('2026-10-01T12:00:00Z'))

  expect(range).toEqual({
    start: '2026-01-02',
    end: '2026-10-01',
    contextStart: '2025-01-01',
    contextEnd: '2025-12-31',
    contextYear: 2025,
    testYear: 2026,
  })
})
