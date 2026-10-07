import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'

import { CalibrationTable } from './CalibrationTable'

test('empty bins explain that HOLD is not scored', () => {
  render(
    <CalibrationTable
      buckets={[
        { low: '0', high: '0.2', count: 0, hit_rate: null, mean_confidence: null },
        { low: '0.2', high: '0.4', count: 0, hit_rate: null, mean_confidence: null },
        { low: '0.4', high: '0.6', count: 0, hit_rate: null, mean_confidence: null },
        { low: '0.6', high: '0.8', count: 0, hit_rate: null, mean_confidence: null },
        { low: '0.8', high: '1', count: 0, hit_rate: null, mean_confidence: null },
      ]}
    />,
  )

  expect(screen.getByText(/HOLD is not used/)).toBeInTheDocument()
})

test('a filled bin shows the hit rate', () => {
  render(
    <CalibrationTable
      buckets={[
        { low: '0', high: '0.2', count: 0, hit_rate: null, mean_confidence: null },
        { low: '0.2', high: '0.4', count: 0, hit_rate: null, mean_confidence: null },
        { low: '0.4', high: '0.6', count: 0, hit_rate: null, mean_confidence: null },
        { low: '0.6', high: '0.8', count: 0, hit_rate: null, mean_confidence: null },
        { low: '0.8', high: '1', count: 2, hit_rate: '1', mean_confidence: '0.9' },
      ]}
    />,
  )

  expect(screen.getByText('2')).toBeInTheDocument()
  expect(screen.getByText('100.00 %')).toBeInTheDocument()
})
