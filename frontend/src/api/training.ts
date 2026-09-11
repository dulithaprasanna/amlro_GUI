import {
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import { apiGet, apiPost } from './client';
import { datasetKey } from './dataset';
import { experimentKey } from './experiments';
import type { TrainingNextResult, TrainingTable } from './types';

const trainingTableKey = (experimentId: string) =>
  ['experiments', experimentId, 'training'] as const;

function getTrainingTable(experimentId: string): Promise<TrainingTable> {
  return apiGet(`/api/experiments/${experimentId}/training`);
}

function postTrainingNext(
  experimentId: string,
  objValues?: unknown[],
): Promise<TrainingNextResult> {
  return apiPost(`/api/experiments/${experimentId}/training/next`, {
    obj_values: objValues,
  });
}

export function useTrainingTable(experimentId: string) {
  return useQuery({
    queryKey: trainingTableKey(experimentId),
    queryFn: () => getTrainingTable(experimentId),
    enabled: Boolean(experimentId),
  });
}

export function useTrainingNext(experimentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (objValues?: unknown[]) =>
      postTrainingNext(experimentId, objValues),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: trainingTableKey(experimentId),
      });
      queryClient.invalidateQueries({ queryKey: experimentKey(experimentId) });
      queryClient.invalidateQueries({ queryKey: datasetKey(experimentId) });
    },
  });
}

const trainingInitKey = (experimentId: string) =>
  ['experiments', experimentId, 'training', 'init'] as const;

/**
 * Primes the training loop (the equivalent of the old app's first GET
 * /training) — a POST with a real side effect (it writes the reaction-data
 * header on AMLRO's side) that must run at most once per experiment.
 *
 * This is deliberately a useQuery, not a useMutation triggered from an
 * effect + ref guard: the query cache is keyed by experimentId and lives in
 * the QueryClient (created once at the app root), so it survives a
 * remount of the calling component — a plain component-local ref does not,
 * and calling this twice would silently corrupt the training data (AMLRO's
 * write_data_to_training_files only writes the header on the very first
 * call, regardless of what's passed in).
 */
export function useTrainingInit(experimentId: string, enabled: boolean) {
  const queryClient = useQueryClient();
  return useQuery({
    queryKey: trainingInitKey(experimentId),
    queryFn: async () => {
      const result = await postTrainingNext(experimentId);
      queryClient.invalidateQueries({ queryKey: trainingTableKey(experimentId) });
      queryClient.invalidateQueries({ queryKey: experimentKey(experimentId) });
      return result;
    },
    enabled,
    retry: false,
    staleTime: Infinity,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });
}
