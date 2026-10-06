import { ColorType, LineSeries, createChart } from 'lightweight-charts'
import { useEffect, useRef } from 'react'

import type { LinePoint } from '../api/liveChart'

type Props = {
  agents: LinePoint[]
  benchmark: LinePoint[]
  index?: LinePoint[]
}

export function EquityChart({ agents, benchmark, index = [] }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const container = containerRef.current
    if (container === null || (agents.length === 0 && benchmark.length === 0 && index.length === 0)) {
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
      timeScale: { borderColor: '#e2e8f0', timeVisible: true, secondsVisible: false },
    })
    const agentsSeries = chart.addSeries(LineSeries, { color: '#0f172a', lineWidth: 2, title: 'Agents' })
    const holdSeries = chart.addSeries(LineSeries, {
      color: '#94a3b8',
      lineWidth: 2,
      title: 'Buy and hold',
    })
    try {
      if (agents.length > 0) {
        agentsSeries.setData(agents)
      }
      if (benchmark.length > 0) {
        holdSeries.setData(benchmark)
      }
      if (index.length > 0) {
        const indexSeries = chart.addSeries(LineSeries, {
          color: '#2563eb',
          lineWidth: 2,
          title: 'CAC 40',
        })
        indexSeries.setData(index)
      }
    } catch {
      chart.remove()
      return
    }
    chart.timeScale().fitContent()

    return () => {
      chart.remove()
    }
  }, [agents, benchmark, index])

  if (agents.length === 0 && benchmark.length === 0 && index.length === 0) {
    return (
      <p className="px-4 py-12 text-center text-sm text-slate-500">
        No equity point yet. The first mark is stored after the next open cycle.
      </p>
    )
  }

  return <div ref={containerRef} className="h-72 w-full" />
}
