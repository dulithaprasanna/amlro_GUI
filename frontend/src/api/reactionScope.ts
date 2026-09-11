import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiPost } from './client';
import { experimentKey } from './experiments';
import type { ExperimentConfig, ExperimentState } from './types';

function createReactionScope(
  experimentId: string,
  config: ExperimentConfig,
): Promise<ExperimentState> {
  return apiPost(`/api/experiments/${experimentId}/reaction-scope`, config);
}

export function useCreateReactionScope(experimentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (config: ExperimentConfig) =>
      createReactionScope(experimentId, config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: experimentKey(experimentId) });
    },
  });
}
