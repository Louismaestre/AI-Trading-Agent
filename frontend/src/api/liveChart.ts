import type { UTCTimestamp } from 'lightweight-charts'

import type { EquityPoint, IntradayBar, Order } from './types'

export type UtcCandle = {
  time: UTCTimestamp
  open: number
  high: number
  low: number
  close: number
}

export type LinePoint = {
  time: UTCTimestamp
  value: number
}

export type TradeMarker = {
  time: UTCTimestamp
  position: 'belowBar' | 'aboveBar'
  color: string
  shape: 'arrowUp' | 'arrowDown'
  text: string
}

export function toUtcSeconds(iso: string): UTCTimestamp {
  return Math.floor(new Date(iso).getTime() / 1000) as UTCTimestamp
}

export function floorToFiveMinutes(iso: string): UTCTimestamp {
  const slot = 5 * 60
  return (Math.floor(toUtcSeconds(iso) / slot) * slot) as UTCTimestamp
}

export function equityToLine(points: EquityPoint[]): LinePoint[] {
  const line: LinePoint[] = []
  for (const point of points) {
    const time = toUtcSeconds(point.recorded_at)
    const value = Number(point.total_value)
    const last = line[line.length - 1]
    if (last !== undefined && last.time === time) {
      last.value = value
      continue
    }
    line.push({ time, value })
  }
  return line
}

export function intradayToCandles(bars: IntradayBar[]): UtcCandle[] {
  return bars.map((bar) => ({
    time: toUtcSeconds(bar.timestamp),
    open: Number(bar.open),
    high: Number(bar.high),
    low: Number(bar.low),
    close: Number(bar.close),
  }))
}

export function orderMarkers(orders: Order[], ticker: string): TradeMarker[] {
  return orders
    .filter((order) => order.ticker === ticker && order.status === 'FILLED' && order.executed_at)
    .map((order) => {
      const buy = order.side === 'BUY'
      return {
        time: floorToFiveMinutes(order.executed_at as string),
        position: buy ? 'belowBar' : 'aboveBar',
        color: buy ? '#047857' : '#b91c1c',
        shape: buy ? 'arrowUp' : 'arrowDown',
        text: order.side,
      }
    })
}

export function intradayStartIso(nowIso: string): string {
  const start = new Date(nowIso)
  start.setUTCDate(start.getUTCDate() - 2)
  return start.toISOString()
}
