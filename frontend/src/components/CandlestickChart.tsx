import { CandlestickSeries, ColorType, createChart } from 'lightweight-charts'
import { useEffect, useRef } from 'react'

import type { Candle } from '../api/chart'

type Props = {
  candles: Candle[]
}

export function CandlestickChart({ candles }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const container = containerRef.current
    if (container === null || candles.length === 0) {
      return
    }

    const chart = createChart(container, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: '#ffffff' },
        textColor: '#475569',
      },
      grid: {
        vertLines: { color: '#f1f5f9' },
        horzLines: { color: '#f1f5f9' },
      },
      rightPriceScale: { borderColor: '#e2e8f0' },
      timeScale: { borderColor: '#e2e8f0' },
    })
    const series = chart.addSeries(CandlestickSeries, {
      upColor: '#047857',
      downColor: '#b91c1c',
      borderVisible: false,
      wickUpColor: '#047857',
      wickDownColor: '#b91c1c',
    })
    series.setData(candles)
    chart.timeScale().fitContent()

    return () => {
      chart.remove()
    }
  }, [candles])

  if (candles.length === 0) {
    return (
      <p className="px-4 py-16 text-center text-sm text-slate-500">
        No daily bars stored for this period. Sync prices from the API docs, then refresh.
      </p>
    )
  }

  return <div ref={containerRef} className="h-[28rem] w-full" />
}
