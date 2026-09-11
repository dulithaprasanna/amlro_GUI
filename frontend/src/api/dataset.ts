import { useQuery } from '@tanstack/react-query';
import { apiGet } from './client';
import type { FullDataset } from './types';

export const datasetKey = (experimentId: string) =>
  ['experiments', experimentId, 'dataset'] as const;

function getFullDataset(experimentId: string): Promise<FullDataset> {
  return apiGet(`/api/experiments/${experimentId}/dataset`);
}

/**
 * The full accumulated dataset (training rows + every submitted prediction
 * batch) for the objective trajectory chart and dataset table — invalidated
 * alongside the experiment whenever training/prediction advances, so it
 * always reflects what's actually been recorded.
 */
export function useFullDataset(experimentId: string, enabled = true) {
  return useQuery({
    queryKey: datasetKey(experimentId),
    queryFn: () => getFullDataset(experimentId),
    enabled: Boolean(experimentId) && enabled,
  });
}
