import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'

import type { AgentDecisionDetail } from '../api/types'
import { DebateSection, ReportsSection, RiskSection } from './DecisionPage'

const decision: AgentDecisionDetail = {
  id: 1,
  ticker: 'MC.PA',
  as_of: '2026-09-15',
  created_at: '2026-09-15T08:00:00Z',
  action: 'BUY',
  confidence: 0.8,
  target_weight: 0.1,
  rationale: 'RSI oversold',
  llm_model: 'fake',
  duration_ms: 12,
  order_id: null,
  reports: {
    sentiment: { stance: 'NEUTRAL', confidence: 0.2, rationale: 'No headlines at as_of.' },
  },
  debate: [{ side: 'BULL', conviction: 0.7, argument: 'RSI bounce' }],
  risk: {
    approved: false,
    action: 'HOLD',
    target_weight: 0,
    reasons: ['crowded luxury book'],
    triggered_rules: ['llm_refused'],
  },
}

test('reports debate and risk sections render the stored trace', () => {
  render(
    <>
      <ReportsSection reports={decision.reports} />
      <DebateSection debate={decision.debate} />
      <RiskSection risk={decision.risk} />
    </>,
  )

  expect(screen.getByText(/sentiment · NEUTRAL/)).toBeInTheDocument()
  expect(screen.getByText(/RSI bounce/)).toBeInTheDocument()
  expect(screen.getByText(/Refused/)).toBeInTheDocument()
  expect(screen.getByText(/llm_refused/)).toBeInTheDocument()
})

test('empty trace shows the fallback copy', () => {
  render(
    <>
      <ReportsSection reports={{}} />
      <DebateSection debate={[]} />
      <RiskSection risk={null} />
    </>,
  )

  expect(screen.getByText(/No specialist report/)).toBeInTheDocument()
  expect(screen.getByText(/No debate/)).toBeInTheDocument()
  expect(screen.getByText(/Risk manager was off/)).toBeInTheDocument()
})
