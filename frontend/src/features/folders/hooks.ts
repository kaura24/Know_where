import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { createFolder, deleteFolder, fetchFolders } from './api';
import type { CreateFolderPayload } from './types';

export function useFoldersQuery() {
  return useQuery({
    queryKey: ['folders'],
    queryFn: fetchFolders,
  });
}

export function useCreateFolderMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateFolderPayload) => createFolder(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['folders'] });
    },
  });
}

export function useDeleteFolderMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (folderId: number) => deleteFolder(folderId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['folders'] });
      queryClient.invalidateQueries({ queryKey: ['cards'] });
    },
  });
}
