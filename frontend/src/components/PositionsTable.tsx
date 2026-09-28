import { formatEuro, positionPnl } from '../api/money'
import type { Position } from '../api/types'

export function PositionsTable({ positions }: { positions: Position[] }) {
  if (positions.length === 0) {
    return <p className="text-sm text-slate-500">No open position.</p>
  }

  return (
    <table className="w-full text-left text-sm">
      <thead className="text-slate-500">
        <tr>
          <th className="py-2 font-medium">Ticker</th>
          <th className="py-2 font-medium">Qty</th>
          <th className="py-2 font-medium">Avg cost</th>
          <th className="py-2 font-medium">Value</th>
          <th className="py-2 font-medium">P&L</th>
        </tr>
      </thead>
      <tbody>
        {positions.map((position) => {
          const pnl = positionPnl(position.quantity, position.average_cost, position.value)
          return (
            <tr key={position.ticker} className="border-t border-slate-200">
              <td className="py-2 font-medium">{position.ticker}</td>
              <td className="py-2">{position.quantity}</td>
              <td className="py-2">{formatEuro(position.average_cost)}</td>
              <td className="py-2">{formatEuro(position.value)}</td>
              <td className={`py-2 ${pnl >= 0 ? 'text-emerald-700' : 'text-red-700'}`}>
                {formatEuro(pnl)}
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
