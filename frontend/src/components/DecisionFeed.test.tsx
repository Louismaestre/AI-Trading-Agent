import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'

import type { AgentDecision, Order } from '../api/types'
import { DecisionFeed } from './DecisionFeed'

const decision: AgentDecision = {
  id: 1,
  ticker: 'MC.PA',
  as_of: '2026-09-29',
  created_at: '2026-09-29T08:00:00Z',
  action: 'BUY',
  confidence: 0.8,
  target_weight: 0.1,
  rationale: 'RSI oversold',
  llm_model: 'fake',
  duration_ms: 12,
  order_id: 4,
}

const order: Order = {
  id: 4,
  ticker: 'MC.PA',
  side: 'BUY',
  quantity: 12,
  status: 'FILLED',
  decision_at: '2026-09-29T08:00:00Z',
  executed_at: '2026-09-29T08:05:00Z',
  execution_price: '610.0000',
  fees: '3.0000',
  rejection_reason: null,
}

test('the feed shows time, action, order and rationale', () => {
  render(<DecisionFeed decisions={[decision]} orders={[order]} />)

  expect(screen.getByText('BUY')).toBeInTheDocument()
  expect(screen.getByText('BUY 12')).toBeInTheDocument()
  expect(screen.getByText(/RSI oversold/)).toBeInTheDocument()
  expect(screen.getByText(/MC.PA/)).toBeInTheDocument()
})

test('HOLD rows have no order size', () => {
  render(
    <DecisionFeed
      decisions={[{ ...decision, action: 'HOLD', order_id: null, rationale: 'wait' }]}
      orders={[]}
    />,
  )

  expect(screen.getByText('HOLD')).toBeInTheDocument()
  expect(screen.getByText('—')).toBeInTheDocument()
  expect(screen.getByText(/wait/)).toBeInTheDocument()
})
