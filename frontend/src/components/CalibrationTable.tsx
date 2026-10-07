import { formatPercent } from '../api/money'
import type { CalibrationBucket } from '../api/types'

export function CalibrationTable({ buckets }: { buckets: CalibrationBucket[] }) {
  if (buckets.every((bucket) => bucket.count === 0)) {
    return (
      <p className="text-sm text-slate-500">
        No directional call to score. HOLD is not used for calibration.
      </p>
    )
  }

  return (
    <table className="w-full text-left text-sm">
      <thead className="text-xs tracking-wide text-slate-500 uppercase">
        <tr>
          <th className="py-2 font-medium">Confidence</th>
          <th className="py-2 font-medium">Calls</th>
          <th className="py-2 font-medium">Hit rate</th>
        </tr>
      </thead>
      <tbody>
        {buckets.map((bucket) => (
          <tr key={`${bucket.low}-${bucket.high}`} className="border-t border-slate-100">
            <td className="py-2">
              {formatPercent(bucket.low)} – {formatPercent(bucket.high)}
            </td>
            <td className="py-2">{bucket.count}</td>
            <td className="py-2">
              {bucket.hit_rate === null ? '—' : formatPercent(bucket.hit_rate)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
