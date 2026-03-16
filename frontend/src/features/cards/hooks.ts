import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { createCard, deleteCard, fetchCard, fetchCards, retryCardJobs, updateCard } from './api';
import type { CreateCardPayload, UpdateCardPayload } from './types';

export function useCardsQuery(
  folderId?: number,
  query?: string,
  sort: 'created_at_desc' | 'created_at_asc' = 'created_at_desc',
) {
  return useQuery({
    queryKey: ['cards', folderId ?? null, query ?? '', sort],
    queryFn: () => fetchCards({ folderId, query, sort }),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) {
        return false;
      }
      const hasPendingJob = data.results.some(
        (card) => card.thumbnail_status === 'pending' || card.thumbnail_status === 'processing' || card.ingestion_status === 'pending' || card.ingestion_status === 'processing',
      );
      return hasPendingJob ? 5000 : false;
    },
  });
}

export function useCardDetailQuery(cardId: number | null) {
  return useQuery({
    queryKey: ['card', cardId],
    queryFn: () => fetchCard(cardId as number),
    enabled: cardId !== null,
    refetchInterval: (query) => {
      const card = query.state.data;
      if (!card) {
        return false;
      }
      const isPending =
        card.thumbnail_status === 'pending' ||
        card.thumbnail_status === 'processing' ||
        card.ingestion_status === 'pending' ||
        card.ingestion_status === 'processing';
      return isPending ? 5000 : false;
    },
  });
}

export function useCreateCardMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateCardPayload) => createCard(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cards'] });
      queryClient.invalidateQueries({ queryKey: ['folders'] });
    },
  });
}

export function useUpdateCardMutation(cardId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: UpdateCardPayload) => updateCard(cardId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cards'] });
      queryClient.invalidateQueries({ queryKey: ['card', cardId] });
    },
  });
}

export function useUpdateAnyCardMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ cardId, payload }: { cardId: number; payload: UpdateCardPayload }) => updateCard(cardId, payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['cards'] });
      queryClient.invalidateQueries({ queryKey: ['card', variables.cardId] });
      queryClient.invalidateQueries({ queryKey: ['folders'] });
    },
  });
}

export function useDeleteCardMutation(cardId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => deleteCard(cardId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cards'] });
      queryClient.invalidateQueries({ queryKey: ['folders'] });
      queryClient.removeQueries({ queryKey: ['card', cardId] });
    },
  });
}

export function useDeleteAnyCardMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (cardId: number) => deleteCard(cardId),
    onSuccess: (_, cardId) => {
      queryClient.invalidateQueries({ queryKey: ['cards'] });
      queryClient.invalidateQueries({ queryKey: ['folders'] });
      queryClient.removeQueries({ queryKey: ['card', cardId] });
    },
  });
}

export function useRetryCardJobsMutation(cardId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => retryCardJobs(cardId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cards'] });
      queryClient.invalidateQueries({ queryKey: ['card', cardId] });
    },
  });
}

export function useRetryAnyCardJobsMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (cardId: number) => retryCardJobs(cardId),
    onSuccess: (_, cardId) => {
      queryClient.invalidateQueries({ queryKey: ['cards'] });
      queryClient.invalidateQueries({ queryKey: ['card', cardId] });
    },
  });
}
