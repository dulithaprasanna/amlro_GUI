import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost } from './client';
import { datasetKey } from './dataset';
import { experimentKey } from './experiments';
import type {
  CurrentBatchResult,
  ExperimentState,
  PredictionNextResult,
} from './types';

interface SubmitBatchInput {
  parameters: unknown[][];
  objectives: unknown[][];
  stop?: boolean;
  batch_size?: number;
}

function getCurrentBatch(experimentId: string): Promise<CurrentBatchResult> {
  return apiGet(`/api/experiments/${experimentId}/prediction`);
}

function postSubmitBatch(
  experimentId: string,
  input: SubmitBatchInput,
): Promise<PredictionNextResult> {
  return apiPost(`/api/experiments/${experimentId}/prediction/next`, input);
}

export function usePredictionNext(experimentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: SubmitBatchInput) => postSubmitBatch(experimentId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: experimentKey(experimentId) });
      queryClient.invalidateQueries({ queryKey: datasetKey(experimentId) });
    },
  });
}

function postUpdateBatchSize(
  experimentId: string,
  batchSize: number,
): Promise<ExperimentState> {
  return apiPost(`/api/experiments/${experimentId}/prediction/batch-size`, {
    batch_size: batchSize,
  });
}

// Deliberately includes the prediction cycle's iteration number, not just
// the experiment id. With staleTime: Infinity (see useCurrentBatch below),
// a key that stayed the same across cycles would mean navigating away
// after cycle 1 and back during cycle 2 serves cycle 1's cached result
// straight out of the cache — the query never actually re-fetches, even
// though a fresh GET would correctly return cycle 2's batch. Each cycle
// getting its own cache entry makes that impossible: an iteration that's
// never been fetched before has nothing to serve, so it always fetches.
const currentBatchKey = (experimentId: string, iteration?: number) =>
  ['experiments', experimentId, 'prediction', 'current-batch', iteration] as const;

/**
 * Persists a batch size change immediately, independent of submitting a
 * batch — mirrors the old app's separate "Update Batch Size" action.
 * Without this, changing batch size but not submitting yet (e.g. before
 * navigating away) would be silently lost, since nothing had actually told
 * the server to change it.
 */
export function useUpdateBatchSize(experimentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (batchSize: number) => postUpdateBatchSize(experimentId, batchSize),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: experimentKey(experimentId) });
      // No iteration given — matches every cached iteration for this
      // experiment (React Query treats a shorter key as a prefix match).
      queryClient.invalidateQueries({
        queryKey: currentBatchKey(experimentId).slice(0, -1),
      });
    },
  });
}

/**
 * Fetches the batch AMLRO currently recommends, without submitting or
 * writing anything — a genuine GET, safe to call any number of times (e.g.
 * after reloading mid-cycle, before the pending batch's results have been
 * entered). Deliberately not auto-refetching within a cycle: retraining is
 * expensive (~seconds to ~a minute), and re-running it wouldn't give a
 * *new* batch — it's deterministic for a given training set.
 */
export function useCurrentBatch(experimentId: string, iteration: number, enabled: boolean) {
  return useQuery({
    queryKey: currentBatchKey(experimentId, iteration),
    queryFn: () => getCurrentBatch(experimentId),
    enabled,
    retry: false,
    staleTime: Infinity,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });
}

function postResumeOptimization(experimentId: string): Promise<ExperimentState> {
  return apiPost(`/api/experiments/${experimentId}/prediction/resume`);
}

/**
 * Reopens a stopped/completed experiment. Nothing about the recorded data
 * changes — the next fetch of the current batch just retrains on whatever's
 * already there and predicts from there, same as resuming mid-cycle.
 */
export function useResumeOptimization(experimentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => postResumeOptimization(experimentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: experimentKey(experimentId) });
    },
  });
}
