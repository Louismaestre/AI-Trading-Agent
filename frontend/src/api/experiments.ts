import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { getJson, postJson } from './http'
import { replayKeys } from './replay'
import type { Experiment, ExperimentRun } from './types'

export const experimentKeys = {
  list: ['experiments'] as const,
}

export function listExperiments(): Promise<Experiment[]> {
  return getJson('/api/v1/experiments')
}

export function startExperiment(id: string, repeats = 1): Promise<ExperimentRun> {
  return postJson(`/api/v1/experiments/${id}/replays?repeats=${repeats}`, {})
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
    mutationFn: ({ id, repeats }: { id: string; repeats: number }) => startExperiment(id, repeats),
    onSuccess: (run) => {
      const replay = run.repeats[0]
      if (replay !== undefined) {
        queryClient.setQueryData(replayKeys.replay(replay.id), replay)
      }
    },
  })
}
