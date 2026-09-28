import type { Bar } from './types'

export type Candle = {
  time: string
  open: number
  high: number
  low: number
  close: number
}

export type DayChange = {
  close: number
  change: number
  percent: number
}

export function barsToCandles(bars: Bar[]): Candle[] {
  return bars.map((bar) => ({
    time: bar.date,
    open: Number(bar.open),
    high: Number(bar.high),
    low: Number(bar.low),
    close: Number(bar.close),
  }))
}

export function lastDayChange(bars: Bar[]): DayChange | null {
  if (bars.length === 0) {
    return null
  }
  const close = Number(bars[bars.length - 1].close)
  if (bars.length === 1) {
    return { close, change: 0, percent: 0 }
  }
  const previous = Number(bars[bars.length - 2].close)
  const change = close - previous
  return { close, change, percent: previous === 0 ? 0 : (change / previous) * 100 }
}

export function isoDate(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function defaultPriceRange(): { start: string; end: string } {
  const end = new Date()
  const start = new Date()
  start.setFullYear(end.getFullYear() - 2)
  return { start: isoDate(start), end: isoDate(end) }
}
