import { useEffect, useState } from 'react'

import { remainingLabel } from '../api/countdown'
import type { LiveSessionStatus, MarketStatus } from '../api/types'

type Props = {
  market: MarketStatus
  nextCycleAt: string | null
  sessionStatus: LiveSessionStatus | null
}

export function MarketClock({ market, nextCycleAt, sessionStatus }: Props) {
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 1000)
    return () => window.clearInterval(id)
  }, [])
  const marketLabel = market.is_open
    ? 'Market open'
    : `Market closed · opens in ${remainingLabel(now, new Date(market.next_open))}`
  const cycleLabel = cycleText(sessionStatus, nextCycleAt, now)

  return (
    <div className="flex flex-wrap gap-3 text-sm">
      <span className={market.is_open ? 'text-emerald-700' : 'text-slate-500'}>{marketLabel}</span>
      {cycleLabel ? <span className="text-slate-600">{cycleLabel}</span> : null}
    </div>
  )
}

function cycleText(
  status: LiveSessionStatus | null,
  nextCycleAt: string | null,
  now: Date,
): string | null {
  if (status === 'PAUSED') {
    return 'Session paused'
  }
  if (status === 'STOPPED') {
    return 'Session stopped'
  }
  if (status === 'RUNNING' && nextCycleAt !== null) {
    return `Next cycle in ${remainingLabel(now, new Date(nextCycleAt))}`
  }
  return null
}
