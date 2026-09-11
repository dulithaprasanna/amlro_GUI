import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiPostForm } from './client';
import { experimentKey } from './experiments';
import type { DataUploadResult } from './types';

function uploadReactionData(
  experimentId: string,
  file: File,
  fileName: string,
): Promise<DataUploadResult> {
  const form = new FormData();
  form.append('file', file);
  form.append('file_name', fileName);
  return apiPostForm(`/api/experiments/${experimentId}/data`, form);
}

export function useUploadReactionData(experimentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ file, fileName }: { file: File; fileName: string }) =>
      uploadReactionData(experimentId, file, fileName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: experimentKey(experimentId) });
    },
  });
}
