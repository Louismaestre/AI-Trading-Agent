import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { getOrders, queryKeys } from './client'
import { getJson, postJson } from './http'
import type {
  AgentDecision,
  EquityPoint,
  IntradayBar,
  LiveSession,
  MarketStatus,
  StartLiveSessionBody,
} from './types'

export const LIVE_POLL_MS = 30_000

export const liveKeys = {
  market: ['market-status'] as const,
  session: (id: number) => ['live-session', id] as const,
  equity: (id: number) => ['live-equity', id] as const,
  decisions: (id: number) => ['live-decisions', id] as const,
  intraday: (ticker: string, start: string) => ['intraday', ticker, start] as const,
}

export function getMarketStatus(): Promise<MarketStatus> {
  return getJson('/api/v1/market/status')
}

export function startLiveSession(body: StartLiveSessionBody = {}): Promise<LiveSession> {
  return postJson('/api/v1/live-sessions', body)
}

export function getLiveSession(id: number): Promise<LiveSession> {
  return getJson(`/api/v1/live-sessions/${id}`)
}

export function pauseLiveSession(id: number): Promise<LiveSession> {
  return postJson(`/api/v1/live-sessions/${id}/pause`, {})
}

export function resumeLiveSession(id: number): Promise<LiveSession> {
  return postJson(`/api/v1/live-sessions/${id}/resume`, {})
}

export function stopLiveSession(id: number): Promise<LiveSession> {
  return postJson(`/api/v1/live-sessions/${id}/stop`, {})
}

export function getLiveEquity(id: number): Promise<EquityPoint[]> {
  return getJson(`/api/v1/live-sessions/${id}/equity`)
}

export function getLiveDecisions(id: number): Promise<AgentDecision[]> {
  return getJson(`/api/v1/live-sessions/${id}/decisions`)
}

export function getIntraday(ticker: string, start: string): Promise<IntradayBar[]> {
  const params = new URLSearchParams({ start })
  return getJson(`/api/v1/instruments/${encodeURIComponent(ticker)}/intraday?${params}`)
}

export function useMarketStatus() {
  return useQuery({
    queryKey: liveKeys.market,
    queryFn: getMarketStatus,
    refetchInterval: LIVE_POLL_MS,
  })
}

export function useLiveSession(id: number | null) {
  return useQuery({
    queryKey: liveKeys.session(id ?? 0),
    queryFn: () => getLiveSession(id as number),
    enabled: id !== null,
    refetchInterval: LIVE_POLL_MS,
  })
}

export function useLiveEquity(id: number | null) {
  return useQuery({
    queryKey: liveKeys.equity(id ?? 0),
    queryFn: () => getLiveEquity(id as number),
    enabled: id !== null,
    refetchInterval: LIVE_POLL_MS,
  })
}

export function useLiveDecisions(id: number | null) {
  return useQuery({
    queryKey: liveKeys.decisions(id ?? 0),
    queryFn: () => getLiveDecisions(id as number),
    enabled: id !== null,
    refetchInterval: LIVE_POLL_MS,
  })
}

export function useLiveOrders(id: number | null) {
  return useQuery({
    queryKey: queryKeys.orders(id ?? 0),
    queryFn: () => getOrders(id as number),
    enabled: id !== null,
    refetchInterval: LIVE_POLL_MS,
  })
}

export function useIntraday(ticker: string, start: string | null) {
  return useQuery({
    queryKey: liveKeys.intraday(ticker, start ?? ''),
    queryFn: () => getIntraday(ticker, start as string),
    enabled: Boolean(ticker && start),
    refetchInterval: LIVE_POLL_MS,
  })
}

export function useStartLiveSession() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: StartLiveSessionBody) => startLiveSession(body),
    onSuccess: (session) => {
      queryClient.setQueryData(liveKeys.session(session.id), session)
    },
  })
}

export function useLiveControl(sessionId: number) {
  const queryClient = useQueryClient()

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: liveKeys.session(sessionId) })
    void queryClient.invalidateQueries({ queryKey: liveKeys.equity(sessionId) })
  }

  const pause = useMutation({
    mutationFn: () => pauseLiveSession(sessionId),
    onSuccess: invalidate,
  })
  const resume = useMutation({
    mutationFn: () => resumeLiveSession(sessionId),
    onSuccess: invalidate,
  })
  const stop = useMutation({
    mutationFn: () => stopLiveSession(sessionId),
    onSuccess: invalidate,
  })
  return { pause, resume, stop }
}
