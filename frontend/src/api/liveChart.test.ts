import { expect, test } from 'vitest'

import { equityToLine, floorToFiveMinutes, orderMarkers } from './liveChart'
import type { EquityPoint, Order } from './types'

test('equityToLine keeps the last value when two points share a second', () => {
  const points: EquityPoint[] = [
    { id: 1, recorded_at: '2026-09-29T08:00:00Z', total_value: '100000', cash: '100000' },
    { id: 2, recorded_at: '2026-09-29T08:00:00Z', total_value: '99400', cash: '2000' },
  ]

  expect(equityToLine(points)).toEqual([
    { time: Math.floor(Date.parse('2026-09-29T08:00:00Z') / 1000), value: 99400 },
  ])
})

test('orderMarkers keep filled trades on the selected ticker', () => {
  const orders: Order[] = [
    {
      id: 1,
      ticker: 'MC.PA',
      side: 'BUY',
      quantity: 2,
      status: 'FILLED',
      decision_at: '2026-09-29T08:01:00Z',
      executed_at: '2026-09-29T08:07:00Z',
      execution_price: '610',
      fees: '1',
      rejection_reason: null,
    },
    {
      id: 2,
      ticker: 'OR.PA',
      side: 'SELL',
      quantity: 1,
      status: 'FILLED',
      decision_at: '2026-09-29T08:01:00Z',
      executed_at: '2026-09-29T08:07:00Z',
      execution_price: '400',
      fees: '1',
      rejection_reason: null,
    },
  ]

  expect(orderMarkers(orders, 'MC.PA')).toEqual([
    {
      time: floorToFiveMinutes('2026-09-29T08:07:00Z'),
      position: 'belowBar',
      color: '#047857',
      shape: 'arrowUp',
      text: 'BUY',
    },
  ])
})
