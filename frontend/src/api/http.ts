/** Shared fetch helper: JSON in, throw on a non-2xx status. */

const FETCH_TIMEOUT_MS = 12_000

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)
  try {
    const response = await fetch(path, { ...init, signal: controller.signal })
    if (!response.ok) {
      throw new Error(await httpErrorMessage(response))
    }
    return (await response.json()) as T
  } catch (error) {
    if (isAbortError(error)) {
      throw new Error(
        'API timeout. Restart `make run` if a replay blocked the server, then refresh.',
      )
    }
    throw error
  } finally {
    clearTimeout(timer)
  }
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException
    ? error.name === 'AbortError'
    : error instanceof Error && error.name === 'AbortError'
}

async function httpErrorMessage(response: Response): Promise<string> {
  const status = `${response.status} ${response.statusText}`.trim()
  try {
    const body = (await response.json()) as { detail?: unknown }
    if (typeof body.detail === 'string' && body.detail.length > 0) {
      return `${status} · ${body.detail}`
    }
  } catch {
    return status
  }
  return status
}

export function getJson<T>(path: string): Promise<T> {
  return requestJson<T>(path)
}

export function postJson<T>(path: string, body: unknown): Promise<T> {
  return requestJson<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}
