import { expect, test, vi } from 'vitest'

import { getHealth } from './health'

test('getHealth reads the JSON body when the API answers 200', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: 'ok', environment: 'local', database: 'ok' }),
    }),
  )

  await expect(getHealth()).resolves.toEqual({
    status: 'ok',
    environment: 'local',
    database: 'ok',
  })
})

test('getHealth throws when the API answers an error', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({ ok: false, status: 503 }),
  )

  await expect(getHealth()).rejects.toThrow('Health check failed (503)')
})
