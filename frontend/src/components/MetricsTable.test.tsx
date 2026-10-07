import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'

import { MetricsTable } from './MetricsTable'

test('the table shows return, drawdown, ratios, orders, fees and hit rate', () => {
  render(
    <MetricsTable
      metrics={{
        total_return: '0.1',
        max_drawdown: '0.25',
        order_count: 4,
        fees_paid: '12.5',
        hit_rate: '0.5',
        volatility: '0.12',
        sharpe: '1.5',
        sortino: '1.8',
        calibration: [],
      }}
    />,
  )

  expect(screen.getByText('10.00 %')).toBeInTheDocument()
  expect(screen.getByText('25.00 %')).toBeInTheDocument()
  expect(screen.getByText('12.00 %')).toBeInTheDocument()
  expect(screen.getByText('1.50')).toBeInTheDocument()
  expect(screen.getByText('1.80')).toBeInTheDocument()
  expect(screen.getByText('4')).toBeInTheDocument()
  expect(screen.getByText('50.00 %')).toBeInTheDocument()
})
