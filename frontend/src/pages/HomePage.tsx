import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Bookmark,
  Bot,
  Copy,
  FolderPlus,
  ExternalLink,
  Folder,
  LayoutGrid,
  Link as LinkIcon,
  List,
  Loader2,
  PenLine,
  Plus,
  Power,
  RefreshCcw,
  Search,
  Settings2,
  Trash2,
  User,
  X,
} from 'lucide-react';

import {
  useCardDetailQuery,
  useCardsQuery,
  useCreateCardMutation,
  useDeleteAnyCardMutation,
  useDeleteCardMutation,
  useRetryAnyCardJobsMutation,
  useRetryCardJobsMutation,
  useUpdateAnyCardMutation,
  useUpdateCardMutation,
} from '../features/cards/hooks';
import {
  useCreateFolderMutation,
  useDeleteFolderMutation,
  useFoldersQuery,
} from '../features/folders/hooks';
import type { CardListItem } from '../features/cards/types';
import { http, resolveApiAssetUrl } from '../lib/http';

const ALL_FOLDER_ID = -1;
const APP_ZOOM_STORAGE_KEY = 'know-where-app-zoom';
const UI_VERSION_STORAGE_KEY = 'know-where-ui-version';
const UI_THEME_STORAGE_KEY = 'know-where-ui-theme';
const COLOR_THEME_STORAGE_KEY = 'know-where-color-theme';
const CARD_VIEW_MODE_STORAGE_KEY = 'know-where-card-view-mode';
type UiVersion = 'old' | 'new';
type UiTheme = 'ui-theme-1' | 'ui-theme-2' | 'ui-theme-3';
type ColorTheme = 'color-theme-1' | 'color-theme-2' | 'color-theme-3';
type CardViewMode = 'grid' | 'list';
type CardSortOrder = 'created_at_desc' | 'created_at_asc';
type SaveProgressTone = 'running' | 'success' | 'error';

function clampZoom(value: number) {
  return Math.min(1.4, Math.max(0.8, Number(value.toFixed(2))));
}

function formatCreatedAt(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '-';
  }
  return new Intl.DateTimeFormat('ko-KR', {
    year: '2-digit',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date);
}

export function HomePage() {
  const [activeFolder, setActiveFolder] = useState<number>(ALL_FOLDER_ID);
  const [searchQuery, setSearchQuery] = useState('');
  const [urlInput, setUrlInput] = useState('');
  const [selectedCardId, setSelectedCardId] = useState<number | null>(null);
  const [draggedCardId, setDraggedCardId] = useState<number | null>(null);
  const [dropFolderId, setDropFolderId] = useState<number | null>(null);
  const [folderPickerCardId, setFolderPickerCardId] = useState<number | null>(null);
  const [isCreatingFolder, setIsCreatingFolder] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isShuttingDown, setIsShuttingDown] = useState(false);
  const [sortOrder, setSortOrder] = useState<CardSortOrder>('created_at_desc');
  const [saveProgress, setSaveProgress] = useState<{ tone: SaveProgressTone; message: string } | null>(null);
  const [trackingCardId, setTrackingCardId] = useState<number | null>(null);
  const saveProgressTimerRef = useRef<number | null>(null);
  const [appZoom, setAppZoom] = useState<number>(() => {
    if (typeof window === 'undefined') {
      return 1;
    }
    const rawValue = Number(window.localStorage.getItem(APP_ZOOM_STORAGE_KEY) ?? '1');
    return Number.isFinite(rawValue) ? clampZoom(rawValue) : 1;
  });
  const [uiVersion, setUiVersion] = useState<UiVersion>(() => {
    if (typeof window === 'undefined') {
      return 'old';
    }
    return window.localStorage.getItem(UI_VERSION_STORAGE_KEY) === 'new' ? 'new' : 'old';
  });
  const [uiTheme, setUiTheme] = useState<UiTheme>(() => {
    if (typeof window === 'undefined') {
      return 'ui-theme-1';
    }
    const savedTheme = window.localStorage.getItem(UI_THEME_STORAGE_KEY);
    return savedTheme === 'ui-theme-2' || savedTheme === 'ui-theme-3' ? savedTheme : 'ui-theme-1';
  });
  const [colorTheme, setColorTheme] = useState<ColorTheme>(() => {
    if (typeof window === 'undefined') {
      return 'color-theme-1';
    }
    const savedTheme = window.localStorage.getItem(COLOR_THEME_STORAGE_KEY);
    return savedTheme === 'color-theme-2' || savedTheme === 'color-theme-3' ? savedTheme : 'color-theme-1';
  });
  const [cardViewMode, setCardViewMode] = useState<CardViewMode>(() => {
    if (typeof window === 'undefined') {
      return 'grid';
    }
    return window.localStorage.getItem(CARD_VIEW_MODE_STORAGE_KEY) === 'list' ? 'list' : 'grid';
  });

  const foldersQuery = useFoldersQuery();
  const cardsQuery = useCardsQuery(activeFolder === ALL_FOLDER_ID ? undefined : activeFolder, searchQuery, sortOrder);
  const createCardMutation = useCreateCardMutation();
  const createFolderMutation = useCreateFolderMutation();
  const deleteFolderMutation = useDeleteFolderMutation();
  const deleteCardMutation = useDeleteAnyCardMutation();
  const retryCardJobsMutation = useRetryAnyCardJobsMutation();
  const updateAnyCardMutation = useUpdateAnyCardMutation();

  const folders = foldersQuery.data ?? [];
  const cards = cardsQuery.data?.results ?? [];
  const selectedCardPreview = cards.find((card) => card.id === selectedCardId) ?? null;
  const activeFolderEntity = folders.find((folder) => folder.id === activeFolder) ?? null;
  const isCreateFlowRunning = createCardMutation.isPending || trackingCardId !== null;

  const activeFolderName = useMemo(() => {
    if (activeFolder === ALL_FOLDER_ID) {
      return '전체 지식';
    }
    return folders.find((folder) => folder.id === activeFolder)?.name ?? '폴더';
  }, [activeFolder, folders]);

  useEffect(() => {
    document.body.style.zoom = String(appZoom);
    window.localStorage.setItem(APP_ZOOM_STORAGE_KEY, String(appZoom));
  }, [appZoom]);

  useEffect(() => {
    document.documentElement.dataset.uiVersion = uiVersion;
    window.localStorage.setItem(UI_VERSION_STORAGE_KEY, uiVersion);
  }, [uiVersion]);

  useEffect(() => {
    document.documentElement.dataset.uiTheme = uiTheme;
    window.localStorage.setItem(UI_THEME_STORAGE_KEY, uiTheme);
  }, [uiTheme]);

  useEffect(() => {
    document.documentElement.dataset.colorTheme = colorTheme;
    window.localStorage.setItem(COLOR_THEME_STORAGE_KEY, colorTheme);
  }, [colorTheme]);

  useEffect(() => {
    window.localStorage.setItem(CARD_VIEW_MODE_STORAGE_KEY, cardViewMode);
  }, [cardViewMode]);

  useEffect(() => {
    if (!cardsQuery.dataUpdatedAt) {
      return;
    }
    void foldersQuery.refetch();
  }, [cardsQuery.dataUpdatedAt]);

  useEffect(
    () => () => {
      if (saveProgressTimerRef.current !== null) {
        window.clearTimeout(saveProgressTimerRef.current);
      }
    },
    [],
  );

  useEffect(() => {
    if (trackingCardId === null) {
      return;
    }

    let isCancelled = false;
    let isChecking = false;

    async function checkStatus() {
      if (isCancelled || isChecking) {
        return;
      }
      isChecking = true;
      try {
        const status = await http<{ ingestion_status: string; ingestion_error: string | null }>(`/cards/${trackingCardId}/status/`);
        if (isCancelled) {
          return;
        }

        const aiRunning = status.ingestion_status === 'pending' || status.ingestion_status === 'processing';
        if (aiRunning) {
          setSaveProgress((current) => {
            const nextMessage = '저장 완료 · AI 처리 중...';
            if (current?.tone === 'running' && current.message === nextMessage) {
              return current;
            }
            return { tone: 'running', message: nextMessage };
          });
          return;
        }

        setTrackingCardId(null);
        if (saveProgressTimerRef.current !== null) {
          window.clearTimeout(saveProgressTimerRef.current);
          saveProgressTimerRef.current = null;
        }
        if (status.ingestion_status === 'failed') {
          setSaveProgress({
            tone: 'error',
            message: `저장은 완료됐지만 AI 처리에 실패했습니다.${status.ingestion_error ? ` (${status.ingestion_error})` : ''}`,
          });
        }
        else {
          setSaveProgress({
            tone: 'success',
            message: '저장 및 AI 처리가 완료되었습니다.',
          });
        }
        saveProgressTimerRef.current = window.setTimeout(() => {
          setSaveProgress(null);
          saveProgressTimerRef.current = null;
        }, 4500);
      }
      catch (error) {
        if (isCancelled) {
          return;
        }
        setTrackingCardId(null);
        setSaveProgress({
          tone: 'error',
          message: error instanceof Error ? `처리 상태 확인 실패: ${error.message}` : '처리 상태 확인에 실패했습니다.',
        });
      }
      finally {
        isChecking = false;
      }
    }

    void checkStatus();
    const intervalId = window.setInterval(() => {
      void checkStatus();
    }, 2500);

    return () => {
      isCancelled = true;
      window.clearInterval(intervalId);
    };
  }, [trackingCardId]);

  function handleCreateCard() {
    const nextUrl = urlInput.trim();
    if (!nextUrl || isCreateFlowRunning) {
      return;
    }

    if (saveProgressTimerRef.current !== null) {
      window.clearTimeout(saveProgressTimerRef.current);
      saveProgressTimerRef.current = null;
    }
    setSaveProgress({ tone: 'running', message: '저장 요청 전송 중...' });
    setTrackingCardId(null);

    createCardMutation.mutate(
      {
        folder_id: activeFolder === ALL_FOLDER_ID ? undefined : activeFolder,
        url: nextUrl,
      },
      {
        onSuccess: (createdCard) => {
          setTrackingCardId(createdCard.id);
          setSaveProgress({ tone: 'running', message: '저장 완료 · AI 처리 대기 중...' });
        },
        onError: (error) => {
          setTrackingCardId(null);
          setSaveProgress({
            tone: 'error',
            message: error instanceof Error ? `저장 실패: ${error.message}` : '저장 요청에 실패했습니다.',
          });
          saveProgressTimerRef.current = window.setTimeout(() => {
            setSaveProgress(null);
            saveProgressTimerRef.current = null;
          }, 5000);
        },
      },
    );
    setUrlInput('');
  }

  async function handleCopy(url: string) {
    await navigator.clipboard.writeText(url);
  }

  function handleCreateFolder() {
    const name = newFolderName.trim();
    if (!name) {
      return;
    }
    createFolderMutation.mutate(
      { name, color: 'blue' },
      {
        onSuccess: (folder) => {
          setNewFolderName('');
          setIsCreatingFolder(false);
          setActiveFolder(folder.id);
        },
      },
    );
  }

  function handleDeleteActiveFolder() {
    if (!activeFolderEntity || activeFolderEntity.is_system) {
      return;
    }
    const confirmed = window.confirm(`'${activeFolderEntity.name}' 폴더를 삭제하시겠습니까?`);
    if (!confirmed) {
      return;
    }
    deleteFolderMutation.mutate(activeFolderEntity.id, {
      onSuccess: () => {
        setActiveFolder(ALL_FOLDER_ID);
        window.alert('삭제되었습니다.');
      },
    });
  }

  function handleDeleteCard(cardId: number) {
    const targetCard = cards.find((card) => card.id === cardId);
    const confirmed = window.confirm(`'${targetCard?.title ?? '이 카드'}'를 삭제하시겠습니까?`);
    if (!confirmed) {
      return;
    }
    deleteCardMutation.mutate(cardId, {
      onSuccess: () => {
        if (selectedCardId === cardId) {
          setSelectedCardId(null);
        }
        window.alert('삭제되었습니다.');
      },
    });
  }

  function handleRefreshCard(cardId: number) {
    const targetCard = cards.find((card) => card.id === cardId);
    const confirmed = window.confirm(`'${targetCard?.title ?? '이 카드'}' 정보를 현재 AI 기준으로 다시 받아오시겠습니까?`);
    if (!confirmed) {
      return;
    }
    retryCardJobsMutation.mutate(cardId, {
      onSuccess: () => {
        window.alert('새로 고침이 시작되었습니다.');
      },
      onError: (error) => {
        window.alert(error instanceof Error ? error.message : '새로 고침에 실패했습니다.');
      },
    });
  }

  function handleMoveCardToFolder(cardId: number, folderId: number) {
    const targetCard = cards.find((card) => card.id === cardId);
    const targetFolder = folders.find((folder) => folder.id === folderId);
    if (!targetCard || !targetFolder || targetCard.folder_id === folderId) {
      return;
    }
    updateAnyCardMutation.mutate(
      {
        cardId,
        payload: { folder_id: folderId },
      },
      {
        onSuccess: () => {
          window.alert(`'${targetCard.title}' 카드가 '${targetFolder.name}' 폴더로 이동되었습니다.`);
        },
        onError: (error) => {
          window.alert(error instanceof Error ? error.message : '폴더 이동에 실패했습니다.');
        },
        onSettled: () => {
          setDraggedCardId(null);
          setDropFolderId(null);
          setFolderPickerCardId(null);
        },
      },
    );
  }

  async function handleShutdown() {
    if (isShuttingDown) {
      return;
    }

    const confirmed = window.confirm('Know Where 실행 프로세스를 안전하게 종료할까요?');
    if (!confirmed) {
      return;
    }

    setIsShuttingDown(true);
    try {
      await http<{ status: string }>('/health/shutdown/', { method: 'POST' });
      window.setTimeout(() => {
        window.close();
      }, 800);
    }
    catch (error) {
      window.alert(error instanceof Error ? error.message : '종료 요청에 실패했습니다.');
      setIsShuttingDown(false);
    }
  }

  useEffect(() => {
    function handleWheel(event: WheelEvent) {
      if (!event.ctrlKey) {
        return;
      }
      event.preventDefault();
      setAppZoom((current) => clampZoom(current + (event.deltaY < 0 ? 0.05 : -0.05)));
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (!event.ctrlKey) {
        return;
      }

      if (event.key === '+' || event.key === '=') {
        event.preventDefault();
        setAppZoom((current) => clampZoom(current + 0.05));
      }
      else if (event.key === '-') {
        event.preventDefault();
        setAppZoom((current) => clampZoom(current - 0.05));
      }
      else if (event.key === '0') {
        event.preventDefault();
        setAppZoom(1);
      }
    }

    window.addEventListener('wheel', handleWheel, { passive: false });
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      window.removeEventListener('wheel', handleWheel);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  return (
    <div className={`app-shell ui-version-${uiVersion}`}>
      <header className="topbar">
        <div className="brand-block">
          <div className="brand-mark">
            <Bookmark size={18} />
          </div>
          <div>
            <div className="brand-title">KnowledgeHub</div>
            <div className="brand-status">
              <Bot size={12} />
              <span>Connected · GPT-5</span>
            </div>
          </div>
        </div>

        <div className="toolbar-center">
          <div className="input-shell-wrap">
            <div className="input-shell">
              <Plus size={16} />
              <input
                value={urlInput}
                onChange={(event) => setUrlInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !isCreateFlowRunning) {
                    handleCreateCard();
                  }
                }}
                placeholder="새로운 URL을 붙여넣어 지식을 저장하세요..."
              />
              <button type="button" onClick={handleCreateCard} disabled={isCreateFlowRunning}>
                {createCardMutation.isPending ? (
                  <>
                    <Loader2 size={16} className="spin" />
                    저장 요청 중
                  </>
                ) : trackingCardId !== null ? (
                  <>
                    <Loader2 size={16} className="spin" />
                    AI 처리 중...
                  </>
                ) : (
                  '저장'
                )}
              </button>
            </div>
            {saveProgress ? (
              <div className={`save-progress save-progress-${saveProgress.tone}`}>{saveProgress.message}</div>
            ) : null}
          </div>

          <div className="search-shell">
            <Search size={16} />
            <input
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="저장된 지식 검색..."
            />
            {searchQuery ? (
              <button type="button" className="ghost-icon" onClick={() => setSearchQuery('')}>
                <X size={14} />
              </button>
            ) : null}
          </div>
        </div>

        <div className="toolbar-right">
          <button
            type="button"
            className="zoom-badge"
            onClick={() => setAppZoom(1)}
            title="배율 초기화 (Ctrl+0)"
          >
            {Math.round(appZoom * 100)}%
          </button>
          <div className="view-mode-toggle" role="group" aria-label="카드 보기 방식">
            <button
              type="button"
              className={`view-mode-option ${cardViewMode === 'grid' ? 'is-active' : ''}`}
              onClick={() => setCardViewMode('grid')}
              title="카드형 보기"
              aria-label="카드형 보기"
            >
              <LayoutGrid size={14} />
            </button>
            <button
              type="button"
              className={`view-mode-option ${cardViewMode === 'list' ? 'is-active' : ''}`}
              onClick={() => setCardViewMode('list')}
              title="목록형 보기"
              aria-label="목록형 보기"
            >
              <List size={14} />
            </button>
          </div>
          <button
            type="button"
            className="ghost-icon danger-icon"
            onClick={() => void handleShutdown()}
            title="안전 종료"
            disabled={isShuttingDown}
          >
            <Power size={16} />
          </button>
          <button
            type="button"
            className={`ghost-icon ${isSettingsOpen ? 'is-active' : ''}`}
            onClick={() => setIsSettingsOpen(true)}
            title="설정"
          >
            <Settings2 size={16} />
          </button>
        </div>
      </header>

      <div className="body-shell">
        <aside className="sidebar">
          <div className="sidebar-header">
            <span>내 폴더</span>
            <div className="sidebar-actions">
              {activeFolderEntity && !activeFolderEntity.is_system ? (
                <button
                  type="button"
                  className="ghost-icon"
                  onClick={handleDeleteActiveFolder}
                  disabled={deleteFolderMutation.isPending}
                  title="폴더 삭제"
                >
                  <Trash2 size={14} />
                </button>
              ) : null}
              <button
                type="button"
                className="ghost-icon"
                onClick={() => setIsCreatingFolder((prev) => !prev)}
                title="폴더 추가"
              >
                <FolderPlus size={14} />
              </button>
            </div>
          </div>
          {isCreatingFolder ? (
            <div className="folder-create-panel">
              <input
                value={newFolderName}
                onChange={(event) => setNewFolderName(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    handleCreateFolder();
                  }
                }}
                placeholder="새 폴더 이름"
              />
              <div className="editor-actions">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => {
                    setIsCreatingFolder(false);
                    setNewFolderName('');
                  }}
                >
                  취소
                </button>
                <button
                  type="button"
                  className="primary-button"
                  onClick={handleCreateFolder}
                  disabled={createFolderMutation.isPending}
                >
                  {createFolderMutation.isPending ? <Loader2 size={14} className="spin" /> : '추가'}
                </button>
              </div>
            </div>
          ) : null}
          <button
            type="button"
            className={`folder-item ${activeFolder === ALL_FOLDER_ID ? 'active' : ''}`}
            onClick={() => setActiveFolder(ALL_FOLDER_ID)}
          >
            <span className="folder-label">
              <Folder size={14} />
              전체 지식
            </span>
            <span>{cardsQuery.data?.count ?? cards.length}</span>
          </button>
          {folders.map((folder) => (
            <button
              key={folder.id}
              type="button"
              className={`folder-item ${activeFolder === folder.id ? 'active' : ''} ${dropFolderId === folder.id ? 'drop-target' : ''}`}
              onClick={() => setActiveFolder(folder.id)}
              onDragOver={(event) => {
                if (draggedCardId === null) {
                  return;
                }
                event.preventDefault();
                setDropFolderId(folder.id);
              }}
              onDragLeave={() => {
                if (dropFolderId === folder.id) {
                  setDropFolderId(null);
                }
              }}
              onDrop={(event) => {
                event.preventDefault();
                if (draggedCardId !== null) {
                  handleMoveCardToFolder(draggedCardId, folder.id);
                }
              }}
            >
              <span className="folder-label">
                <Folder size={14} />
                {folder.name}
              </span>
              <span>{folder.card_count}</span>
            </button>
          ))}
        </aside>

        <main className="content">
          <div className="content-header">
            <div>
              <h1>{activeFolderName}</h1>
              <p>총 {cardsQuery.data?.count ?? cards.length}개의 지식이 저장되어 있습니다.</p>
            </div>
            <div className="content-header-actions">
              <label className="sort-select-label" htmlFor="card-sort-order">
                정렬
              </label>
              <select
                id="card-sort-order"
                className="sort-select"
                value={sortOrder}
                onChange={(event) => setSortOrder(event.target.value as CardSortOrder)}
              >
                <option value="created_at_desc">최신순</option>
                <option value="created_at_asc">오래된순</option>
              </select>
            </div>
          </div>

          <section className={`card-grid ${cardViewMode === 'list' ? 'list-mode' : ''}`}>
            {cardsQuery.isLoading || createCardMutation.isPending ? <SkeletonCard /> : null}
            {cards.map((card) => (
              <article
                key={card.id}
                className={`card-item ${cardViewMode === 'list' ? 'list-mode' : ''}`}
                onClick={() => setSelectedCardId(card.id)}
                draggable={cardViewMode !== 'list'}
                onDragStart={() => {
                  setDraggedCardId(card.id);
                }}
                onDragEnd={() => {
                  setDraggedCardId(null);
                  setDropFolderId(null);
                }}
              >
                {cardViewMode === 'list' ? (
                  <>
                    <div className="card-title-row">
                      <h3 className="list-card-title">{card.title}</h3>
                      <span className="card-created-at">{formatCreatedAt(card.created_at)}</span>
                    </div>
                    <p className="list-card-summary">{card.summary || '요약이 아직 없습니다.'}</p>
                  </>
                ) : (
                  <>
                    <div className="card-folder-panel card-folder-panel-top">
                      <div className="card-folder-panel-header">
                        <button
                          type="button"
                          className="folder-switcher-button"
                          onClick={(event) => {
                            event.stopPropagation();
                            setFolderPickerCardId((current) => (current === card.id ? null : card.id));
                          }}
                        >
                          <span>{card.folder_name}</span>
                        </button>
                        <div className="card-top-actions">
                          <div className="card-item-actions">
                            <button
                              type="button"
                              className="card-refresh-button"
                              title="카드 새로 고침"
                              onClick={(event) => {
                                event.stopPropagation();
                                handleRefreshCard(card.id);
                              }}
                              disabled={retryCardJobsMutation.isPending}
                            >
                              <RefreshCcw size={14} className={retryCardJobsMutation.isPending ? 'spin' : undefined} />
                            </button>
                            <button
                              type="button"
                              className="card-delete-button"
                              title="카드 삭제"
                              onClick={(event) => {
                                event.stopPropagation();
                                handleDeleteCard(card.id);
                              }}
                              disabled={deleteCardMutation.isPending}
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </div>
                      </div>
                      {folderPickerCardId === card.id ? (
                        <div className="folder-picker-list" onClick={(event) => event.stopPropagation()}>
                          {folders.map((folder) => (
                            <button
                              key={folder.id}
                              type="button"
                              className={`folder-picker-chip ${folder.id === card.folder_id ? 'active' : ''} ${dropFolderId === folder.id ? 'drop-target' : ''}`}
                              onClick={() => handleMoveCardToFolder(card.id, folder.id)}
                              onDragOver={(event) => {
                                if (draggedCardId === null) {
                                  return;
                                }
                                event.preventDefault();
                                setDropFolderId(folder.id);
                              }}
                              onDragLeave={() => {
                                if (dropFolderId === folder.id) {
                                  setDropFolderId(null);
                                }
                              }}
                              onDrop={(event) => {
                                event.preventDefault();
                                event.stopPropagation();
                                if (draggedCardId !== null) {
                                  handleMoveCardToFolder(draggedCardId, folder.id);
                                }
                              }}
                            >
                              {folder.name}
                            </button>
                          ))}
                        </div>
                      ) : null}
                    </div>
                    <ThumbnailPreview card={card} compact />
                    <div className="card-tags">
                      {(card.tag_names ?? []).slice(0, 3).map((tag) => (
                        <span key={tag} className="tag-chip">
                          {tag}
                        </span>
                      ))}
                    </div>
                    <div className="card-title-row">
                      <h3>{card.title}</h3>
                      <span className="card-created-at">{formatCreatedAt(card.created_at)}</span>
                    </div>
                    <p>{card.summary || '요약이 아직 없습니다.'}</p>
                    <div className="status-row">
                      <span className={`status-pill status-${card.ingestion_status}`}>메타데이터 {translateStatus(card.ingestion_status)}</span>
                      <span className={`status-pill status-${card.thumbnail_status}`}>썸네일 {translateStatus(card.thumbnail_status)}</span>
                    </div>
                    {card.has_memo ? (
                      <div className="memo-hint">
                        <PenLine size={12} />
                        메모 있음
                      </div>
                    ) : null}
                    <div className="card-footer">
                      <span className="card-link">
                        <LinkIcon size={12} />
                        {card.source_domain}
                      </span>
                      <button
                        type="button"
                        className="ghost-icon"
                        onClick={(event) => {
                          event.stopPropagation();
                          void handleCopy(card.url);
                        }}
                      >
                        <Copy size={14} />
                      </button>
                    </div>
                  </>
                )}
              </article>
            ))}
            {!cardsQuery.isLoading && cards.length === 0 ? (
              <div className="empty-state">
                <Search size={28} />
                <h3>결과가 없습니다</h3>
                <p>
                  {searchQuery
                    ? `'${searchQuery}'에 해당하는 지식을 찾을 수 없습니다.`
                    : '현재 폴더에 저장된 지식이 없습니다.'}
                </p>
              </div>
            ) : null}
          </section>
        </main>
      </div>

      {selectedCardId !== null ? (
        <DetailModal
          cardId={selectedCardId}
          previewCard={selectedCardPreview}
          onClose={() => setSelectedCardId(null)}
          onCopy={handleCopy}
        />
      ) : null}

      {isSettingsOpen ? (
        <SettingsPanel
          uiVersion={uiVersion}
          uiTheme={uiTheme}
          colorTheme={colorTheme}
          onClose={() => setIsSettingsOpen(false)}
          onSelectUiVersion={setUiVersion}
          onSelectUiTheme={setUiTheme}
          onSelectColorTheme={setColorTheme}
        />
      ) : null}
    </div>
  );
}

interface SettingsPanelProps {
  uiVersion: UiVersion;
  uiTheme: UiTheme;
  colorTheme: ColorTheme;
  onClose: () => void;
  onSelectUiVersion: (version: UiVersion) => void;
  onSelectUiTheme: (theme: UiTheme) => void;
  onSelectColorTheme: (theme: ColorTheme) => void;
}

function SettingsPanel({
  uiVersion,
  uiTheme,
  colorTheme,
  onClose,
  onSelectUiVersion,
  onSelectUiTheme,
  onSelectColorTheme,
}: SettingsPanelProps) {
  return (
    <>
      <button type="button" className="settings-scrim" aria-label="설정 닫기" onClick={onClose} />
      <aside className="settings-panel-layer" aria-label="화면 설정 패널">
        <div className="settings-panel-header">
          <div className="modal-title-block">
            <User size={16} />
            <h2>화면 설정</h2>
          </div>
          <button type="button" className="ghost-icon" onClick={onClose}>
            <X size={18} />
          </button>
        </div>
        <div className="settings-panel-body">
          <fieldset className="settings-group">
            <legend className="settings-label">
              <span className="section-number">01</span>
              UI 버전
            </legend>
            <label className={`theme-choice ${uiVersion === 'old' ? 'selected' : ''}`}>
              <input
                type="radio"
                name="ui-version"
                checked={uiVersion === 'old'}
                onChange={() => onSelectUiVersion('old')}
              />
              <span className="theme-choice-mark" />
              <span className="theme-choice-text">
                <strong>Old</strong>
                <span>현재 코드 기준의 기존 버전</span>
              </span>
            </label>
            <label className={`theme-choice ${uiVersion === 'new' ? 'selected' : ''}`}>
              <input
                type="radio"
                name="ui-version"
                checked={uiVersion === 'new'}
                onChange={() => onSelectUiVersion('new')}
              />
              <span className="theme-choice-mark" />
              <span className="theme-choice-text">
                <strong>New</strong>
                <span>정제된 시각 계층과 표면감을 적용한 버전</span>
              </span>
            </label>
          </fieldset>
          <fieldset className="settings-group">
            <legend className="settings-label">
              <span className="section-number">02</span>
              UI 테마
            </legend>
            <label className={`theme-choice ${uiTheme === 'ui-theme-1' ? 'selected' : ''}`}>
              <input
                type="radio"
                name="ui-theme"
                checked={uiTheme === 'ui-theme-1'}
                onChange={() => onSelectUiTheme('ui-theme-1')}
              />
              <span className="theme-choice-mark" />
              <span className="theme-choice-text">
                <strong>UI 1</strong>
                <span>현재 기본 카드형</span>
              </span>
            </label>
            <label className={`theme-choice ${uiTheme === 'ui-theme-2' ? 'selected' : ''}`}>
              <input
                type="radio"
                name="ui-theme"
                checked={uiTheme === 'ui-theme-2'}
                onChange={() => onSelectUiTheme('ui-theme-2')}
              />
              <span className="theme-choice-mark" />
              <span className="theme-choice-text">
                <strong>UI 2</strong>
                <span>표면 대비를 높인 업무형</span>
              </span>
            </label>
            <label className={`theme-choice ${uiTheme === 'ui-theme-3' ? 'selected' : ''}`}>
              <input
                type="radio"
                name="ui-theme"
                checked={uiTheme === 'ui-theme-3'}
                onChange={() => onSelectUiTheme('ui-theme-3')}
              />
              <span className="theme-choice-mark" />
              <span className="theme-choice-text">
                <strong>UI 3</strong>
                <span>부드러운 입체감 중심형</span>
              </span>
            </label>
          </fieldset>
          <fieldset className="settings-group">
            <legend className="settings-label">
              <span className="section-number">03</span>
              색상 테마
            </legend>
            <label className={`theme-choice ${colorTheme === 'color-theme-1' ? 'selected' : ''}`}>
              <input
                type="radio"
                name="color-theme"
                checked={colorTheme === 'color-theme-1'}
                onChange={() => onSelectColorTheme('color-theme-1')}
              />
              <span className="theme-choice-mark" />
              <span className="theme-choice-text">
                <strong>색상 1</strong>
                <span>코발트 블루</span>
              </span>
            </label>
            <label className={`theme-choice ${colorTheme === 'color-theme-2' ? 'selected' : ''}`}>
              <input
                type="radio"
                name="color-theme"
                checked={colorTheme === 'color-theme-2'}
                onChange={() => onSelectColorTheme('color-theme-2')}
              />
              <span className="theme-choice-mark" />
              <span className="theme-choice-text">
                <strong>색상 2</strong>
                <span>앰버 브라운</span>
              </span>
            </label>
            <label className={`theme-choice ${colorTheme === 'color-theme-3' ? 'selected' : ''}`}>
              <input
                type="radio"
                name="color-theme"
                checked={colorTheme === 'color-theme-3'}
                onChange={() => onSelectColorTheme('color-theme-3')}
              />
              <span className="theme-choice-mark" />
              <span className="theme-choice-text">
                <strong>색상 3</strong>
                <span>포레스트 그린</span>
              </span>
            </label>
          </fieldset>
        </div>
      </aside>
    </>
  );
}

interface DetailModalProps {
  cardId: number;
  previewCard: CardListItem | null;
  onClose: () => void;
  onCopy: (url: string) => Promise<void>;
}

function DetailModal({ cardId, previewCard, onClose, onCopy }: DetailModalProps) {
  const detailQuery = useCardDetailQuery(cardId);
  const updateCardMutation = useUpdateCardMutation(cardId);
  const deleteCardMutation = useDeleteCardMutation(cardId);
  const retryJobsMutation = useRetryCardJobsMutation(cardId);
  const card = detailQuery.data ?? previewCard;
  const [titleDraft, setTitleDraft] = useState('');
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [tagDrafts, setTagDrafts] = useState<string[]>([]);
  const [isEditingTags, setIsEditingTags] = useState(false);
  const [activeTagIndex, setActiveTagIndex] = useState<number | null>(null);
  const [memoDraft, setMemoDraft] = useState('');
  const [isEditingMemo, setIsEditingMemo] = useState(false);
  const modalBodyRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setTitleDraft(card?.title ?? '');
    setIsEditingTitle(false);
    setTagDrafts(card?.tag_names ?? []);
    setIsEditingTags(false);
    setActiveTagIndex(null);
    setMemoDraft(card?.memo ?? '');
    setIsEditingMemo(false);
  }, [cardId, card?.title, card?.memo]);

  useEffect(() => {
    modalBodyRef.current?.scrollTo({ top: 0 });
  }, [cardId]);

  if (!card) {
    return null;
  }
  const currentCard = card;

  function handleSaveMemo() {
    updateCardMutation.mutate(
      { memo: memoDraft },
      {
        onSuccess: () => {
          setIsEditingMemo(false);
        },
      },
    );
  }

  function handleSaveTags() {
    const tags = tagDrafts.map((value) => value.trim()).filter(Boolean);
    updateCardMutation.mutate(
      { tags },
      {
        onSuccess: () => {
          setIsEditingTags(false);
          setActiveTagIndex(null);
        },
      },
    );
  }

  function handleStartTagEditing(tagIndex?: number) {
    setTagDrafts((currentCard.tag_names ?? []).length > 0 ? [...(currentCard.tag_names ?? [])] : ['']);
    setIsEditingTags(true);
    setActiveTagIndex(tagIndex ?? ((currentCard.tag_names ?? []).length > 0 ? 0 : null));
  }

  function handleChangeTag(index: number, value: string) {
    setTagDrafts((current) => current.map((tag, tagIndex) => (tagIndex === index ? value : tag)));
  }

  function handleAddTagField() {
    setTagDrafts((current) => [...current, '']);
    setActiveTagIndex(tagDrafts.length);
  }

  function handleRemoveTag(index: number) {
    setTagDrafts((current) => current.filter((_, tagIndex) => tagIndex !== index));
    setActiveTagIndex((current) => {
      if (current === null) {
        return null;
      }
      if (current === index) {
        return null;
      }
      return current > index ? current - 1 : current;
    });
  }

  function handleSaveTitle() {
    const nextTitle = titleDraft.trim();
    if (!nextTitle) {
      window.alert('제목을 입력하세요.');
      return;
    }
    updateCardMutation.mutate(
      { title: nextTitle },
      {
        onSuccess: () => {
          setIsEditingTitle(false);
        },
      },
    );
  }

  function handleDeleteCard() {
    const confirmed = window.confirm(`'${currentCard.title}'를 삭제하시겠습니까?`);
    if (!confirmed) {
      return;
    }
    deleteCardMutation.mutate(undefined, {
      onSuccess: () => {
        window.alert('삭제되었습니다.');
        onClose();
      },
    });
  }

  function handleRetryJobs() {
    retryJobsMutation.mutate();
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-block">
            {isEditingTitle ? (
              <div className="title-editor-row">
                <input
                  className="title-editor"
                  value={titleDraft}
                  onChange={(event) => setTitleDraft(event.target.value)}
                  placeholder="제목을 입력하세요."
                />
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => {
                    setTitleDraft(currentCard.title);
                    setIsEditingTitle(false);
                  }}
                >
                  취소
                </button>
                <button
                  type="button"
                  className="primary-button"
                  onClick={handleSaveTitle}
                  disabled={updateCardMutation.isPending}
                >
                  {updateCardMutation.isPending ? '저장 중...' : '저장'}
                </button>
              </div>
            ) : (
              <h2>{card.title}</h2>
            )}
            {detailQuery.isFetching ? <span className="status-pill">동기화 중</span> : null}
          </div>
          <div className="modal-actions">
            {!isEditingTitle ? (
              <button
                type="button"
                className="ghost-icon"
                onClick={() => setIsEditingTitle(true)}
                title="제목 편집"
              >
                <PenLine size={16} />
              </button>
            ) : null}
            <button
              type="button"
              className="ghost-icon danger-icon"
              onClick={handleDeleteCard}
              disabled={deleteCardMutation.isPending}
              title="카드 삭제"
            >
              {deleteCardMutation.isPending ? <Loader2 size={16} className="spin" /> : <Trash2 size={16} />}
            </button>
            <button type="button" className="ghost-icon" onClick={onClose}>
              <X size={18} />
            </button>
          </div>
        </div>
        <div className="modal-body" ref={modalBodyRef}>
          <section className="detail-hero">
            <div className="detail-hero-header">
              <h3>
                <span className="section-number">01</span>
                썸네일
              </h3>
              <span className={`status-pill status-${card.thumbnail_status}`}>썸네일 {translateStatus(card.thumbnail_status)}</span>
            </div>
            <ThumbnailPreview card={card} />
          </section>

          <section className="detail-meta">
            <div className="section-number-row">
              <span className="section-number">02</span>
              <span>링크 메타</span>
            </div>
            <div className="link-row">
              <a href={card.url} target="_blank" rel="noreferrer">
                {card.url}
              </a>
              <button type="button" className="ghost-icon" onClick={() => void onCopy(card.url)}>
                <Copy size={14} />
              </button>
            </div>
            <div className="detail-time-row">
              <span>생성일자</span>
              <strong>{formatCreatedAt(card.created_at)}</strong>
            </div>
          </section>

          <section>
            <div className="section-header">
              <h3>
                <span className="section-number">03</span>
                TAG
              </h3>
              <div className="section-actions">
                {!isEditingTags ? (
                  <button type="button" className="inline-action" onClick={() => handleStartTagEditing()}>
                    {(card.tag_names ?? []).length > 0 ? '편집' : '태그 작성'}
                  </button>
                ) : null}
              </div>
            </div>
            {isEditingTags ? (
              <div className="editor-block">
                <div className="tag-editor-list">
                  {tagDrafts.map((tag, index) => (
                    <div key={`${index}-${tag}`} className="tag-editor-row">
                      <input
                        className={`tag-editor ${activeTagIndex === index ? 'is-active' : ''}`}
                        value={tag}
                        onChange={(event) => handleChangeTag(index, event.target.value)}
                        onFocus={() => setActiveTagIndex(index)}
                        placeholder="태그를 입력하세요."
                      />
                      <button
                        type="button"
                        className="ghost-icon danger-icon"
                        title="태그 삭제"
                        onClick={() => handleRemoveTag(index)}
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  ))}
                </div>
                <div className="editor-actions">
                  <button type="button" className="secondary-button" onClick={handleAddTagField}>
                    태그 추가
                  </button>
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => {
                      setTagDrafts(currentCard.tag_names ?? []);
                      setIsEditingTags(false);
                      setActiveTagIndex(null);
                    }}
                  >
                    취소
                  </button>
                  <button
                    type="button"
                    className="primary-button"
                    onClick={handleSaveTags}
                    disabled={updateCardMutation.isPending}
                  >
                    {updateCardMutation.isPending ? '저장 중...' : '저장'}
                  </button>
                </div>
              </div>
            ) : (card.tag_names ?? []).length > 0 ? (
              <div className="card-tags detail-tags">
                {(card.tag_names ?? []).map((tag, index) => (
                  <button
                    key={tag}
                    type="button"
                    className="tag-chip interactive-tag"
                    onClick={() => handleStartTagEditing(index)}
                    title="태그 편집"
                  >
                    {tag}
                  </button>
                ))}
              </div>
            ) : (
              <div className="text-panel">태그가 아직 없습니다.</div>
            )}
          </section>

          <section>
            <div className="section-header">
              <h3>
                <span className="section-number">04</span>
                AI 요약
              </h3>
              {card.ingestion_status === 'failed' || card.thumbnail_status === 'failed' ? (
                <button
                  type="button"
                  className="inline-action"
                  onClick={handleRetryJobs}
                  disabled={retryJobsMutation.isPending}
                >
                  {retryJobsMutation.isPending ? '재시도 중' : '재시도'}
                </button>
              ) : null}
            </div>
            <div className="text-panel selectable-text">{card.summary || '요약이 아직 없습니다.'}</div>
            {card.ingestion_status === 'failed' ? (
              <p className="error-text">메타데이터 처리 실패: {card.ingestion_error ?? '알 수 없는 오류'}</p>
            ) : null}
            {card.thumbnail_status === 'failed' ? (
              <p className="error-text">썸네일 처리 실패: {card.thumbnail_error ?? '알 수 없는 오류'}</p>
            ) : null}
          </section>

          <section>
            <h3>
              <span className="section-number">05</span>
              세부 내용
            </h3>
            <div className="text-panel selectable-text">{card.details || '상세 내용이 아직 없습니다.'}</div>
          </section>

          <section>
            <div className="section-header">
              <h3>
                <span className="section-number">06</span>
                사용자 메모
              </h3>
              {!isEditingMemo ? (
                <button type="button" className="inline-action" onClick={() => setIsEditingMemo(true)}>
                  {card.memo ? '편집' : '메모 작성'}
                </button>
              ) : null}
            </div>

            {isEditingMemo ? (
              <div className="editor-block">
                <textarea
                  className="memo-editor"
                  value={memoDraft}
                  onChange={(event) => setMemoDraft(event.target.value)}
                  placeholder="이 자료에 대한 개인 메모를 남기세요."
                />
                <div className="editor-actions">
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => {
                      setMemoDraft(card.memo ?? '');
                      setIsEditingMemo(false);
                    }}
                  >
                    취소
                  </button>
                  <button
                    type="button"
                    className="primary-button"
                    onClick={handleSaveMemo}
                    disabled={updateCardMutation.isPending}
                  >
                    {updateCardMutation.isPending ? '저장 중...' : '저장'}
                  </button>
                </div>
              </div>
            ) : (
              <div className={`memo-panel ${card.memo ? 'has-content' : 'is-empty'}`}>
                {card.memo || '메모가 아직 없습니다.'}
              </div>
            )}
          </section>
        </div>
        <div className="modal-footer">
          <div className="status-row">
            <span className={`status-pill status-${card.ingestion_status}`}>메타데이터 {translateStatus(card.ingestion_status)}</span>
            <span className={`status-pill status-${card.thumbnail_status}`}>썸네일 {translateStatus(card.thumbnail_status)}</span>
          </div>
          <a href={card.url} target="_blank" rel="noreferrer" className="primary-link">
            원본 사이트 열기
            <ExternalLink size={14} />
          </a>
        </div>
      </div>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="card-item skeleton-card">
      <div className="skeleton-row short" />
      <div className="skeleton-row medium" />
      <div className="skeleton-row long" />
    </div>
  );
}

interface ThumbnailPreviewProps {
  card: CardListItem;
  compact?: boolean;
}

function ThumbnailPreview({ card, compact = false }: ThumbnailPreviewProps) {
  const resolvedThumbnailUrl = resolveApiAssetUrl(card.thumbnail_url);
  const [hasImageError, setHasImageError] = useState(false);

  useEffect(() => {
    setHasImageError(false);
  }, [resolvedThumbnailUrl]);

  function handleOpenThumbnailZoomWindow() {
    if (!resolvedThumbnailUrl) {
      return;
    }
    const popup = window.open(resolvedThumbnailUrl, '_blank');
    if (!popup) {
      window.alert('팝업이 차단되어 확대 창을 열 수 없습니다.');
    }
  }

  if (resolvedThumbnailUrl && !hasImageError) {
    return (
      <div className={`thumbnail-frame ${compact ? 'compact' : 'detail'}`}>
        <img
          src={resolvedThumbnailUrl}
          alt={`${card.title} 썸네일`}
          className="thumbnail-image zoomable-thumbnail"
          loading="lazy"
          onError={() => setHasImageError(true)}
          onDoubleClick={handleOpenThumbnailZoomWindow}
          title="썸네일을 두 번 클릭하면 확대 창이 열립니다."
        />
      </div>
    );
  }

  return (
    <div className={`thumbnail-frame thumbnail-placeholder ${compact ? 'compact' : 'detail'}`}>
      <div className="thumbnail-placeholder-content">
        <LinkIcon size={compact ? 18 : 22} />
        <strong>{card.thumbnail_status === 'ready' ? '썸네일 로드 실패' : '썸네일 없음'}</strong>
        <span>상태: {translateStatus(card.thumbnail_status)}</span>
        {hasImageError ? <span>이미지 경로를 다시 확인해야 합니다.</span> : null}
      </div>
    </div>
  );
}

function translateStatus(status: string) {
  if (status === 'ready') {
    return '완료';
  }
  if (status === 'failed') {
    return '실패';
  }
  if (status === 'processing') {
    return '처리 중';
  }
  return '대기';
}
