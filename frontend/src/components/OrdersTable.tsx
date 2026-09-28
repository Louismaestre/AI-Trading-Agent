import { formatEuro } from '../api/money'
import type { Order } from '../api/types'

export function OrdersTable({ orders }: { orders: Order[] }) {
  if (orders.length === 0) {
    return <p className="text-sm text-slate-500">No order yet.</p>
  }

  return (
    <table className="w-full text-left text-sm">
      <thead className="text-slate-500">
        <tr>
          <th className="py-2 font-medium">When</th>
          <th className="py-2 font-medium">Side</th>
          <th className="py-2 font-medium">Ticker</th>
          <th className="py-2 font-medium">Qty</th>
          <th className="py-2 font-medium">Status</th>
          <th className="py-2 font-medium">Price</th>
        </tr>
      </thead>
      <tbody>
        {orders.map((order) => (
          <tr key={order.id} className="border-t border-slate-200">
            <td className="py-2 text-slate-500">{order.decision_at.slice(0, 16).replace('T', ' ')}</td>
            <td className="py-2">{order.side}</td>
            <td className="py-2">{order.ticker}</td>
            <td className="py-2">{order.quantity}</td>
            <td className="py-2">{order.status}</td>
            <td className="py-2">
              {order.execution_price ? formatEuro(order.execution_price) : '—'}
              {order.rejection_reason ? (
                <span className="block text-xs text-red-700">{order.rejection_reason}</span>
              ) : null}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
