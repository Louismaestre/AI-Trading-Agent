import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { getJson, postJson } from './http'
import type { Bar, Health, Instrument, Order, PlaceOrderBody, Portfolio } from './types'

export const queryKeys = {
  health: ['health'] as const,
  instruments: ['instruments'] as const,
  prices: (ticker: string, start: string, end: string) => ['prices', ticker, start, end] as const,
  portfolio: (id: number) => ['portfolio', id] as const,
  orders: (id: number) => ['orders', id] as const,
}

export function getHealth(): Promise<Health> {
  return getJson('/api/v1/health')
}

export function getInstruments(): Promise<Instrument[]> {
  return getJson('/api/v1/instruments')
}

export function getPrices(ticker: string, start: string, end: string): Promise<Bar[]> {
  const params = new URLSearchParams({ start, end })
  return getJson(`/api/v1/instruments/${encodeURIComponent(ticker)}/prices?${params}`)
}

export function createPortfolio(name = 'Demo'): Promise<Portfolio> {
  return postJson('/api/v1/portfolios', { name })
}

export function getPortfolio(id: number): Promise<Portfolio> {
  return getJson(`/api/v1/portfolios/${id}`)
}

export function getOrders(id: number): Promise<Order[]> {
  return getJson(`/api/v1/portfolios/${id}/orders`)
}

export function placeOrder(portfolioId: number, body: PlaceOrderBody): Promise<Order> {
  return postJson(`/api/v1/portfolios/${portfolioId}/orders`, body)
}

export function useHealth() {
  return useQuery({ queryKey: queryKeys.health, queryFn: getHealth })
}

export function useInstruments() {
  return useQuery({ queryKey: queryKeys.instruments, queryFn: getInstruments })
}

export function usePrices(ticker: string, start: string, end: string) {
  return useQuery({
    queryKey: queryKeys.prices(ticker, start, end),
    queryFn: () => getPrices(ticker, start, end),
    enabled: Boolean(ticker && start && end),
  })
}

export function useCreatePortfolio() {
  return useMutation({ mutationFn: () => createPortfolio() })
}

export function usePortfolio(id: number | null) {
  return useQuery({
    queryKey: queryKeys.portfolio(id ?? 0),
    queryFn: () => getPortfolio(id as number),
    enabled: id !== null,
  })
}

export function useOrders(id: number | null) {
  return useQuery({
    queryKey: queryKeys.orders(id ?? 0),
    queryFn: () => getOrders(id as number),
    enabled: id !== null,
  })
}

export function usePlaceOrder(portfolioId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: PlaceOrderBody) => placeOrder(portfolioId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.portfolio(portfolioId) })
      void queryClient.invalidateQueries({ queryKey: queryKeys.orders(portfolioId) })
    },
  })
}
