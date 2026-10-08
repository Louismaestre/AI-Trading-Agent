/** JSON shapes returned by the FastAPI backend. Decimals arrive as strings. */

export type ComponentStatus = 'ok' | 'error'

export type Health = {
  status: ComponentStatus
  environment: string
  database: ComponentStatus
}

export type Instrument = {
  ticker: string
  name: string
  isin: string | null
  sector: string | null
  currency: string
  is_active: boolean
}

export type Bar = {
  date: string
  open: string
  high: string
  low: string
  close: string
  volume: number
}

export type OrderSide = 'BUY' | 'SELL'
export type OrderStatus = 'PENDING' | 'FILLED' | 'REJECTED'

export type Position = {
  ticker: string
  quantity: number
  average_cost: string
  market_price: string
  value: string
}

export type Order = {
  id: number
  ticker: string
  side: OrderSide
  quantity: number
  status: OrderStatus
  decision_at: string
  executed_at: string | null
  execution_price: string | null
  fees: string | null
  rejection_reason: string | null
}

export type Portfolio = {
  id: number
  name: string
  initial_capital: string
  cash: string
  market_value: string
  total_value: string
  positions: Position[]
}

export type PlaceOrderBody = {
  ticker: string
  side: OrderSide
  quantity: number
  decision_at?: string
  execute_at?: string
}

export type AgentAction = 'BUY' | 'SELL' | 'HOLD'

export type LiveSessionStatus = 'RUNNING' | 'PAUSED' | 'STOPPED'
export type LiveSessionKind = 'AGENTS' | 'BUY_AND_HOLD'

export type LiveSession = {
  id: number
  portfolio_id: number
  kind: LiveSessionKind
  status: LiveSessionStatus
  interval_minutes: number
  started_at: string
  last_slot: string | null
  next_cycle_at: string | null
  total_value: string
  cash: string
  benchmark_session_id: number | null
}

export type EquityPoint = {
  id: number
  recorded_at: string
  total_value: string
  cash: string
}

export type MarketStatus = {
  now: string
  is_open: boolean
  next_open: string
  last_close: string
}

export type IntradayBar = {
  timestamp: string
  open: string
  high: string
  low: string
  close: string
  volume: number
}

export type StartLiveSessionBody = {
  name?: string
  initial_capital?: string
  interval_minutes?: number
}

export type ReplayStatus = 'PENDING' | 'RUNNING' | 'DONE' | 'FAILED'
export type ReplayKind = 'AGENTS' | 'BUY_AND_HOLD' | 'SMA_CROSS' | 'RANDOM'

export type CalibrationBucket = {
  low: string
  high: string
  count: number
  hit_rate: string | null
  mean_confidence: string | null
}

export type ReplayMetrics = {
  total_return: string
  max_drawdown: string
  order_count: number
  fees_paid: string
  hit_rate: string | null
  volatility: string | null
  sharpe: string | null
  sortino: string | null
  calibration: CalibrationBucket[] | null
}

export type Replay = {
  id: number
  portfolio_id: number
  kind: ReplayKind
  status: ReplayStatus
  start_date: string
  end_date: string
  days_done: number
  days_total: number
  current_date: string | null
  decision_frequency: 'DAILY' | 'WEEKLY'
  error_message: string | null
  benchmark_replay_id: number | null
  sma_replay_id: number | null
  random_replay_id: number | null
  experiment_id: string | null
  batch_id: string | null
  repeat_index: number | null
  metrics: ReplayMetrics | null
}

export type ExperimentRun = {
  batch_id: string
  repeats: Replay[]
}

export type SharpeInterval = {
  low: string
  high: string
}

export type SharpeComparison = {
  p_value: string
  significant: boolean
}

export type RepeatSummary = {
  count: number
  mean_return: string
  std_return: string | null
  replay_ids: number[]
}

export type ReplaySignificance = {
  replay_id: number
  batch_id: string | null
  repeat_index: number | null
  sharpe_ci: SharpeInterval | null
  vs_hold: SharpeComparison | null
  vs_sma: SharpeComparison | null
  vs_random: SharpeComparison | null
  batch: RepeatSummary | null
}

export type ExperimentGraph = {
  fundamental: boolean
  sentiment: boolean
  debate_rounds: number
  risk: boolean
  model: string | null
}

export type Experiment = {
  id: string
  name: string
  question: string
  start: string
  end: string
  initial_capital: string
  decision_frequency: 'DAILY' | 'WEEKLY'
  graph: ExperimentGraph
}

export type StartReplayBody = {
  name?: string
  initial_capital?: string
  start: string
  end: string
  decision_frequency?: 'DAILY' | 'WEEKLY'
}

export type AgentDecision = {
  id: number
  ticker: string
  as_of: string
  created_at: string
  action: AgentAction
  confidence: number
  target_weight: number
  rationale: string
  llm_model: string
  duration_ms: number
  order_id: number | null
}

export type AnalystStance = 'BULLISH' | 'BEARISH' | 'NEUTRAL'

export type AnalystReport = {
  stance: AnalystStance
  confidence: number
  rationale: string
}

export type DebateArgument = {
  side: 'BULL' | 'BEAR'
  conviction: number
  argument: string
}

export type RiskAssessment = {
  approved: boolean
  action: AgentAction
  target_weight: number
  reasons: string[]
  triggered_rules: string[]
}

export type AgentDecisionDetail = AgentDecision & {
  reports: Record<string, AnalystReport>
  debate: DebateArgument[]
  risk: RiskAssessment | null
}
