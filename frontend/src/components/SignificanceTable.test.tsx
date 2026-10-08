import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'

import { SignificanceTable } from './SignificanceTable'

test('the table shows the Sharpe interval, baseline tests and repeat mean', () => {
  render(
    <SignificanceTable
      scored={{
        replay_id: 1,
        batch_id: 'abc',
        repeat_index: 0,
        sharpe_ci: { low: '0.10', high: '0.40' },
        vs_hold: { p_value: '0.02', significant: true },
        vs_sma: { p_value: '0.40', significant: false },
        vs_random: null,
        batch: {
          count: 3,
          mean_return: '0.12',
          std_return: '0.03',
          replay_ids: [1, 2, 3],
        },
      }}
    />,
  )

  expect(screen.getByText('0.10 – 0.40')).toBeInTheDocument()
  expect(screen.getByText('p=0.02 · significant')).toBeInTheDocument()
  expect(screen.getByText('p=0.40 · not significant')).toBeInTheDocument()
  expect(screen.getByText('12.00 % ± 3.00 % (n=3)')).toBeInTheDocument()
})
