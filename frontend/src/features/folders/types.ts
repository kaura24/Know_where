export interface Folder {
  id: number;
  name: string;
  slug: string;
  color: string | null;
  sort_order: number;
  is_system: boolean;
  card_count: number;
  created_at: string;
  updated_at: string;
}

export interface CreateFolderPayload {
  name: string;
  color?: string | null;
}
