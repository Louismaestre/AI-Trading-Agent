export type ComponentStatus = 'ok' | 'error'

export type Health = {
  status: ComponentStatus
  environment: string
  database: ComponentStatus
}

export async function getHealth(): Promise<Health> {
  const response = await fetch('/api/v1/health')
  if (!response.ok) {
    throw new Error(`Health check failed (${response.status})`)
  }
  return response.json() as Promise<Health>
}
