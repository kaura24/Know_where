import { http } from '../../lib/http';
import type {
  CardListItem,
  CardStatus,
  CreateCardPayload,
  PaginatedResponse,
  UpdateCardPayload,
} from './types';

export function fetchCards(params: { folderId?: number; query?: string; sort?: 'created_at_desc' | 'created_at_asc' }) {
  const search = new URLSearchParams();
  if (params.folderId) {
    search.set('folder_id', String(params.folderId));
  }
  if (params.query) {
    search.set('q', params.query);
  }
  if (params.sort) {
    search.set('sort', params.sort);
  }
  const suffix = search.toString() ? `?${search.toString()}` : '';
  return http<PaginatedResponse<CardListItem>>(`/cards/${suffix}`);
}

export function fetchCard(cardId: number) {
  return http<CardListItem>(`/cards/${cardId}/`);
}

export function createCard(payload: CreateCardPayload) {
  return http<CardListItem>('/cards/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateCard(cardId: number, payload: UpdateCardPayload) {
  return http<CardListItem>(`/cards/${cardId}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function fetchCardStatus(cardId: number) {
  return http<CardStatus>(`/cards/${cardId}/status/`);
}

export function deleteCard(cardId: number) {
  return http<void>(`/cards/${cardId}/`, {
    method: 'DELETE',
  });
}

export function retryCardJobs(cardId: number) {
  return http<CardListItem>(`/cards/${cardId}/retry-jobs/`, {
    method: 'POST',
  });
}
