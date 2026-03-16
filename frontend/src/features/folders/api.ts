import { http } from '../../lib/http';
import type { CreateFolderPayload, Folder } from './types';

export function fetchFolders() {
  return http<Folder[]>('/folders/');
}

export function createFolder(payload: CreateFolderPayload) {
  return http<Folder>('/folders/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function deleteFolder(folderId: number) {
  return http<void>(`/folders/${folderId}/`, {
    method: 'DELETE',
  });
}
