export type ProcessingStatus = 'pending' | 'processing' | 'ready' | 'failed';

export interface CardListItem {
  id: number;
  folder_id: number;
  folder_name: string;
  url: string;
  normalized_url: string;
  source_domain: string;
  title: string;
  summary: string;
  details: string;
  memo: string;
  tag_names?: string[];
  has_memo: boolean;
  thumbnail_status: ProcessingStatus;
  thumbnail_url: string | null;
  thumbnail_error?: string | null;
  ingestion_status: ProcessingStatus;
  ingestion_error?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CardStatus {
  card_id: number;
  thumbnail_status: ProcessingStatus;
  ingestion_status: ProcessingStatus;
  thumbnail_error: string | null;
  ingestion_error: string | null;
  updated_at: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface CreateCardPayload {
  folder_id?: number;
  url: string;
  title?: string;
  summary?: string;
  details?: string;
  memo?: string;
  tags?: string[];
}

export interface UpdateCardPayload {
  folder_id?: number;
  title?: string;
  summary?: string;
  details?: string;
  memo?: string;
  tags?: string[];
}
