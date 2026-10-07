import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { getJson, postJson } from './http'
import { replayKeys } from './replay'
import type { Experiment, Replay } from './types'

export const experimentKeys = {
  list: ['experiments'] as const,
}

export function listExperiments(): Promise<Experiment[]> {
  return getJson('/api/v1/experiments')
}

export function startExperiment(id: string): Promise<Replay> {
  return postJson(`/api/v1/experiments/${id}/replays`, {})
}

export function useExperiments() {
  return useQuery({
    queryKey: experimentKeys.list,
    queryFn: listExperiments,
  })
}

export function useStartExperiment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => startExperiment(id),
    onSuccess: (replay) => {
      queryClient.setQueryData(replayKeys.replay(replay.id), replay)
    },
  })
}
