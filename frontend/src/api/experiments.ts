import {
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import { apiDelete, apiGet, apiPost } from './client';
import type {
  ExperimentMode,
  ExperimentState,
  ExperimentSummary,
  ScanForExperimentsResult,
} from './types';

const experimentsKey = ['experiments'] as const;
const experimentKey = (id: string) => ['experiments', id] as const;

function listExperiments(): Promise<ExperimentSummary[]> {
  return apiGet('/api/experiments');
}

function createExperiment(input: {
  mode: ExperimentMode;
  id?: string;
  exp_dir?: string;
}): Promise<ExperimentState> {
  return apiPost('/api/experiments', input);
}

function getExperiment(id: string): Promise<ExperimentState> {
  return apiGet(`/api/experiments/${id}`);
}

function removeExperiment(input: { id: string; deleteFiles: boolean }): Promise<void> {
  return apiDelete(
    `/api/experiments/${input.id}?delete_files=${input.deleteFiles}`,
  );
}

function scanForExperiments(rootDir: string): Promise<ScanForExperimentsResult> {
  return apiPost('/api/experiments/scan', { root_dir: rootDir });
}

export function useExperiments() {
  return useQuery({ queryKey: experimentsKey, queryFn: listExperiments });
}

export function useExperiment(id: string) {
  return useQuery({
    queryKey: experimentKey(id),
    queryFn: () => getExperiment(id),
    enabled: Boolean(id),
  });
}

export function useCreateExperiment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createExperiment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: experimentsKey });
    },
  });
}

export function useRemoveExperiment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: removeExperiment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: experimentsKey });
    },
  });
}

export function useScanForExperiments() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: scanForExperiments,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: experimentsKey });
    },
  });
}

export { experimentKey, experimentsKey };
