import { Link } from 'react-router-dom'

import type { AgentDecision } from '../api/types'

export function DecisionsTable({ decisions }: { decisions: AgentDecision[] }) {
  if (decisions.length === 0) {
    return <p className="text-sm text-slate-500">No agent decision yet.</p>
  }

  return (
    <table className="w-full text-left text-sm">
      <thead className="text-slate-500">
        <tr>
          <th className="py-2 font-medium">Date</th>
          <th className="py-2 font-medium">Ticker</th>
          <th className="py-2 font-medium">Action</th>
          <th className="py-2 font-medium">Confidence</th>
          <th className="py-2 font-medium">Rationale</th>
        </tr>
      </thead>
      <tbody>
        {decisions.map((decision) => (
          <tr key={decision.id} className="border-t border-slate-200">
            <td className="py-2 text-slate-500">{decision.as_of}</td>
            <td className="py-2 font-medium">
              <Link
                to={`/decisions/${decision.id}`}
                className="underline-offset-2 hover:underline"
              >
                {decision.ticker}
              </Link>
            </td>
            <td className="py-2">{decision.action}</td>
            <td className="py-2">{(decision.confidence * 100).toFixed(0)} %</td>
            <td className="py-2 text-slate-600">{decision.rationale}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
