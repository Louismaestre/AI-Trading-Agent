import { afterEach, expect, test, vi } from 'vitest'

import { getInstruments, getPrices, placeOrder } from './client'

afterEach(() => {
  vi.unstubAllGlobals()
})

function stubFetch(body: unknown, status = 200): ReturnType<typeof vi.fn> {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 404 ? 'Not Found' : 'OK',
    json: async () => body,
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

test('getInstruments reads the list of instruments', async () => {
  stubFetch([{ ticker: 'MC.PA', name: 'LVMH', isin: null, sector: 'Luxury', currency: 'EUR', is_active: true }])

  const instruments = await getInstruments()

  expect(instruments).toHaveLength(1)
  expect(instruments[0]?.ticker).toBe('MC.PA')
})

test('getPrices builds the query string and encodes the ticker', async () => {
  const fetchMock = stubFetch([])

  await getPrices('^FCHI', '2026-09-01', '2026-09-10')

  expect(fetchMock).toHaveBeenCalledWith(
    '/api/v1/instruments/%5EFCHI/prices?start=2026-09-01&end=2026-09-10',
    undefined,
  )
})

test('placeOrder posts the JSON body', async () => {
  const fetchMock = stubFetch({ id: 1, ticker: 'MC.PA', side: 'BUY', status: 'PENDING' })

  await placeOrder(3, { ticker: 'MC.PA', side: 'BUY', quantity: 10 })

  expect(fetchMock).toHaveBeenCalledWith(
    '/api/v1/portfolios/3/orders',
    expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ ticker: 'MC.PA', side: 'BUY', quantity: 10 }),
    }),
  )
})

test('getPrices throws the HTTP status when the API fails', async () => {
  stubFetch({ detail: 'Unknown ticker' }, 404)

  await expect(getPrices('NOPE.PA', '2026-09-01', '2026-09-10')).rejects.toThrow('404 Not Found')
})
