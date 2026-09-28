import { expect, test } from 'vitest'

import { performancePercent, positionPnl } from './money'

test('performancePercent is the return since the initial capital', () => {
  expect(performancePercent('110000', '100000')).toBe(10)
})

test('positionPnl subtracts the cost basis from the market value', () => {
  expect(positionPnl(10, '100', '1100')).toBe(100)
})
