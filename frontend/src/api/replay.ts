import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { getJson, postJson } from './http'
import type {
  AgentDecision,
  EquityPoint,
  Replay,
  ReplayMetrics,
  ReplaySignificance,
  StartReplayBody,
} from './types'

export const REPLAY_POLL_MS = 1_000
export const REPLAY_IDLE_POLL_MS = 30_000

export const replayKeys = {
  replay: (id: number) => ['replay', id] as const,
  equity: (id: number) => ['replay-equity', id] as const,
  decisions: (id: number) => ['replay-decisions', id] as const,
  metrics: (id: number) => ['replay-metrics', id] as const,
  significance: (id: number) => ['replay-significance', id] as const,
}

export function startReplay(body: StartReplayBody): Promise<Replay> {
  return postJson('/api/v1/replays', body)
}

export function getReplay(id: number): Promise<Replay> {
  return getJson(`/api/v1/replays/${id}`)
}

export function getReplayEquity(id: number): Promise<EquityPoint[]> {
  return getJson(`/api/v1/replays/${id}/equity`)
}

export function getReplayDecisions(id: number): Promise<AgentDecision[]> {
  return getJson(`/api/v1/replays/${id}/decisions`)
}

export function getReplayMetrics(id: number): Promise<ReplayMetrics> {
  return getJson(`/api/v1/replays/${id}/metrics`)
}

export function getReplaySignificance(id: number): Promise<ReplaySignificance> {
  return getJson(`/api/v1/replays/${id}/significance`)
}

function pollWhileRunning(status: Replay['status'] | undefined): number {
  if (status === 'PENDING' || status === 'RUNNING') {
    return REPLAY_POLL_MS
  }
  return REPLAY_IDLE_POLL_MS
}

export function useReplay(id: number | null) {
  return useQuery({
    queryKey: replayKeys.replay(id ?? 0),
    queryFn: () => getReplay(id as number),
    enabled: id !== null,
    refetchInterval: (query) => pollWhileRunning(query.state.data?.status),
  })
}

export function useReplayEquity(id: number | null) {
  const replay = useReplay(id)
  return useQuery({
    queryKey: replayKeys.equity(id ?? 0),
    queryFn: () => getReplayEquity(id as number),
    enabled: id !== null,
    refetchInterval: pollWhileRunning(replay.data?.status),
  })
}

export function useReplayDecisions(id: number | null) {
  const replay = useReplay(id)
  return useQuery({
    queryKey: replayKeys.decisions(id ?? 0),
    queryFn: () => getReplayDecisions(id as number),
    enabled: id !== null,
    refetchInterval: pollWhileRunning(replay.data?.status),
  })
}

export function useReplayMetrics(id: number | null) {
  const replay = useReplay(id)
  return useQuery({
    queryKey: replayKeys.metrics(id ?? 0),
    queryFn: () => getReplayMetrics(id as number),
    enabled: id !== null && replay.data?.status === 'DONE',
  })
}

export function useReplaySignificance(id: number | null) {
  const replay = useReplay(id)
  return useQuery({
    queryKey: replayKeys.significance(id ?? 0),
    queryFn: () => getReplaySignificance(id as number),
    enabled: id !== null && replay.data?.status === 'DONE',
  })
}

export function useStartReplay() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: StartReplayBody) => startReplay(body),
    onSuccess: (replay) => {
      queryClient.setQueryData(replayKeys.replay(replay.id), replay)
    },
  })
}
