import { formatClock } from '../api/countdown'
import type { AgentDecision, Order } from '../api/types'

type Props = {
  decisions: AgentDecision[]
  orders: Order[]
}

export function DecisionFeed({ decisions, orders }: Props) {
  if (decisions.length === 0) {
    return <p className="text-sm text-slate-500">No agent decision yet.</p>
  }

  const byId = new Map(orders.map((order) => [order.id, order]))

  return (
    <ol className="divide-y divide-slate-200">
      {decisions.map((decision) => {
        const order = decision.order_id === null ? undefined : byId.get(decision.order_id)
        return (
          <li key={decision.id} className="grid gap-1 py-3 sm:grid-cols-[7rem_5rem_6rem_1fr] sm:gap-4">
            <time className="text-sm text-slate-500" dateTime={decision.created_at}>
              {formatClock(decision.created_at)}
            </time>
            <span className={`text-sm font-medium ${actionTone(decision.action)}`}>
              {decision.action}
            </span>
            <span className="text-sm text-slate-700">{orderLabel(order)}</span>
            <p className="text-sm text-slate-600">
              <span className="font-medium text-slate-800">{decision.ticker}</span>
              {' · '}
              {decision.rationale}
            </p>
          </li>
        )
      })}
    </ol>
  )
}

function orderLabel(order: Order | undefined): string {
  if (order === undefined) {
    return '—'
  }
  return `${order.side} ${order.quantity}`
}

function actionTone(action: AgentDecision['action']): string {
  if (action === 'BUY') {
    return 'text-emerald-700'
  }
  if (action === 'SELL') {
    return 'text-red-700'
  }
  return 'text-slate-700'
}
