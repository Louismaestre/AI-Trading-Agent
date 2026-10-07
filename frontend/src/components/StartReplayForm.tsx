import { useState, type FormEvent } from 'react'

import { walkForwardRange } from '../api/chart'
import { useExperiments, useStartExperiment } from '../api/experiments'
import { useStartReplay } from '../api/replay'

type Props = {
  onStarted: (replayId: number) => void
}

export function StartReplayForm({ onStarted }: Props) {
  const range = walkForwardRange()
  const start = useStartReplay()
  const startExperiment = useStartExperiment()
  const experiments = useExperiments()
  const [experimentId, setExperimentId] = useState('')
  const [name, setName] = useState('Replay')
  const [capital, setCapital] = useState('100000')
  const [from, setFrom] = useState(range.start)
  const [to, setTo] = useState(range.end)
  const [frequency, setFrequency] = useState<'DAILY' | 'WEEKLY'>('DAILY')
  const selected = experiments.data?.find((item) => item.id === experimentId)
  const pending = start.isPending || startExperiment.isPending

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (experimentId !== '') {
      const replay = await startExperiment.mutateAsync(experimentId)
      onStarted(replay.id)
      return
    }
    const replay = await start.mutateAsync({
      name,
      initial_capital: capital,
      start: from,
      end: to,
      decision_frequency: frequency,
    })
    onStarted(replay.id)
  }

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="mt-6 max-w-md space-y-4">
      <label className="block text-sm">
        <span className="text-slate-500">Experiment</span>
        <select
          value={experimentId}
          onChange={(event) => setExperimentId(event.target.value)}
          className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
        >
          <option value="">Custom window</option>
          {(experiments.data ?? []).map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
      </label>
      {selected ? <p className="text-sm text-slate-500">{selected.question}</p> : null}
      {experimentId === '' ? (
        <>
          <label className="block text-sm">
            <span className="text-slate-500">Name</span>
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            />
          </label>
          <label className="block text-sm">
            <span className="text-slate-500">Capital (€)</span>
            <input
              value={capital}
              onChange={(event) => setCapital(event.target.value)}
              inputMode="decimal"
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            />
          </label>
          <label className="block text-sm">
            <span className="text-slate-500">Start</span>
            <input
              type="date"
              value={from}
              onChange={(event) => setFrom(event.target.value)}
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            />
          </label>
          <label className="block text-sm">
            <span className="text-slate-500">Decision frequency</span>
            <select
              value={frequency}
              onChange={(event) => setFrequency(event.target.value as 'DAILY' | 'WEEKLY')}
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            >
              <option value="DAILY">Every session (more trades)</option>
              <option value="WEEKLY">Once a week</option>
            </select>
          </label>
          <label className="block text-sm">
            <span className="text-slate-500">End</span>
            <input
              type="date"
              value={to}
              onChange={(event) => setTo(event.target.value)}
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            />
          </label>
        </>
      ) : (
        <p className="text-sm text-slate-500">
          {selected?.start} → {selected?.end} · {selected?.decision_frequency} · same costs as every
          replay
        </p>
      )}
      <button
        type="submit"
        disabled={pending}
        className="rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:bg-slate-300"
      >
        {pending ? 'Starting…' : 'Start replay'}
      </button>
      {start.error ? <p className="text-sm text-red-700">{start.error.message}</p> : null}
      {startExperiment.error ? (
        <p className="text-sm text-red-700">{startExperiment.error.message}</p>
      ) : null}
    </form>
  )
}
