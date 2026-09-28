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
