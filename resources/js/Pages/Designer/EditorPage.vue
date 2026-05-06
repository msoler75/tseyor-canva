<script setup>
import axios from 'axios';
import { Icon } from '@iconify/vue';
import { router, usePage } from '@inertiajs/vue3';
import DesignerLayout from '../../Layouts/DesignerLayout.vue';
import EditorTopBar from '../../Components/designer/EditorTopBar.vue';
import EditorInsertSidebar from '../../Components/designer/EditorInsertSidebar.vue';
import EditorCanvasStage from '../../Components/designer/EditorCanvasStage.vue';
import { computed, defineAsyncComponent, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { brochurePagePairForPhysicalPage, filterLabels, initialDesignerState, isBrochureFormat, isHorizontalFormat, objectiveOptions, objectiveRecommendations, resolveObjectiveSizeOptions } from '../../data/designer';
import {
  flushDesignerStatePersistence,
  hydrateDesignerStateFromPage,
  resetDesignerState,
  setDesignerThumbnailDataUrl,
  useDesignerState,
} from '../../composables/useDesignerState';
import { useEditorHistory } from '../../composables/useEditorHistory';
import { useEditorStyles } from '../../composables/useEditorStyles';
import { useEditorSelection } from '../../composables/useEditorSelection';
import { useEditorInteractions } from '../../composables/useEditorInteractions';
import {
  SHAPE_CLIP_PATHS,
  applyFormatToDimensions,
  buildCanvasBackgroundStyle,
  buildCoverImageStyle,
  buildElementBoxStyle as buildSharedElementBoxStyle,
  buildElementContentStyle as buildSharedElementContentStyle,
  buildImageFrameStyle,
  buildImageTintOverlayStyle,
  buildRichEditorContainerStyle as buildSharedRichEditorContainerStyle,
  buildShapeRenderModel,
  buildShapeStyle,
  neonColorOverrideFromLayout,
  parseSizeDetail,
} from '../../utils/editorShared';
import { useLinkedTextBoxSystem } from '../../composables/useLinkedTextBoxSystem';
import { useFrontendLog } from '../../composables/useFrontendLog';
import { dataUrlToFile, extractImageFilesFromDataTransfer, fileToDataUrl, hasFilesInTransfer, isDataImageUrl, isEditableTarget, optimizeImageFile } from '../../utils/imageUploads';

const DesignerAssistant = defineAsyncComponent(() => import('../../Components/designer/DesignerAssistant.vue'));
const EditorContextPanel = defineAsyncComponent(() => import('../../Components/designer/EditorContextPanel.vue'));
const EditorFloatingToolbar = defineAsyncComponent(() => import('../../Components/designer/EditorFloatingToolbar.vue'));
const ExportDialog = defineAsyncComponent(() => import('../../Components/designer/ExportDialog.vue'));
const SelectionOverlay = defineAsyncComponent(() => import('../../Components/designer/SelectionOverlay.vue'));
const TemplateFormModal = defineAsyncComponent(() => import('../../Components/designer/TemplateFormModal.vue'));
const TemplateAdjustmentsPanel = defineAsyncComponent(() => import('../../Components/designer/TemplateAdjustmentsPanel.vue'));

defineProps({ currentStep: String, steps: Array, navigation: Object });
const page = usePage();
// Siempre reset y rehidratar al montar
resetDesignerState();
const state = hydrateDesignerStateFromPage();
// stateRevision protege la persistencia frente a estados viejos;
// templateRevision fuerza el remonte visual del editor rico al reaplicar plantillas.
const bumpRevision = (value) => Number(value ?? 0) + 1;
const isMobileEditor = ref(false);
let editorViewportQuery = null;

const linkedTextBoxSystem = useLinkedTextBoxSystem();
const frontendLog = useFrontendLog();

const syncEditorViewport = () => {
  isMobileEditor.value = typeof window !== 'undefined'
    ? window.matchMedia('(max-width: 767px)').matches
    : false;
};

// Estado para mostrar el modal de exportación
const exportDialogOpen = ref(false);
const templateFormOpen = ref(false);
const templateFormSaving = ref(false);
const adminTemplates = ref([]);
const shouldOpenTemplateForm = new URLSearchParams(window.location.search).has('templateForm');
const templateForm = reactive({
  uuid: null,
  title: '',
  description: '',
  categoryIds: [],
  objectiveIds: [],
  fieldMappings: [],
  status: 'published',
  featured: false,
  sortOrder: 0,
});

// Estado y lógica del asistente modal.
const assistantOpen = ref(false);
const assistantStep = ref('objective');
const openAssistant = (step = 'objective', resetCurrentDesign = true) => {
  try {
    commitTextEdit();
  } catch (_) {
    // no-op: abrir el asistente no debe depender del estado interno del editor rico
  }
  state.mode = 'guided';
  if (resetCurrentDesign) {
    state.templateCategory = 'all';
    state.currentDesignUuid = null;
    state.designSurface = null;
  }
  assistantStep.value = step;
  assistantOpen.value = true;
};

const closeAssistant = () => {
  assistantOpen.value = false;
};
const openAssistantStep = async (step) => {
  openAssistant(step, false);
};
if (!state.customElements || Array.isArray(state.customElements)) {
  state.customElements = Object.fromEntries(Object.entries(state.customElements ?? {}));
}
if (!state.userUploadedImages) {
  state.userUploadedImages = [];
}

const clonePlain = (value) => JSON.parse(JSON.stringify(value ?? null));
const createPageId = () => `page-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
const documentRevision = ref(0);
const documentPageList = ref([]);
const documentPageRefs = new Map();
const canvasGridRef = ref(null);
const linkedTextOverlayRevision = ref(0);
const copiedElements = ref([]);
const legacyPersistedActivePageId = Reflect.get(state, 'activePageId');
const activePageId = ref(String(legacyPersistedActivePageId ?? state.pages?.[0]?.id ?? 'page-1'));
const workingDocumentPageId = ref(activePageId.value);
const visuallyFocusedPageId = ref(null);
let visiblePageFrame = null;
let isSwitchingDocumentPage = false;
if (Object.prototype.hasOwnProperty.call(state, 'activePageId')) {
  Reflect.deleteProperty(state, 'activePageId');
}
const refreshDocumentPageList = () => {
  documentPageList.value = clonePlain(state.pages ?? []);
};
const clonePageFromState = (id = workingDocumentPageId.value ?? activePageId.value ?? createPageId()) => ({
  id,
  content: clonePlain(state.content ?? initialDesignerState.content),
  elementLayout: clonePlain(state.elementLayout ?? initialDesignerState.elementLayout),
  customElements: clonePlain(state.customElements ?? {}),
});
const createBlankElementLayout = () => ({
  background: clonePlain(initialDesignerState.elementLayout.background),
});
const createBlankPage = ({ includeBaseFields = !isBrochureDocument() } = {}) => ({
  id: createPageId(),
  content: clonePlain(initialDesignerState.content),
  elementLayout: includeBaseFields
    ? clonePlain(initialDesignerState.elementLayout)
    : createBlankElementLayout(),
  customElements: {},
});
const createBlankPages = (count) => Array.from({ length: Math.max(0, count) }, () => createBlankPage());
const isBrochureDocument = (snapshot = state) => isBrochureFormat(snapshot?.format);
const minimumDocumentPageCount = (snapshot = state) => (isBrochureDocument(snapshot) ? 2 : 1);
const isEmptyPageContent = (content = {}) => Object.values(content ?? {}).every((value) => !String(value ?? '').trim());
const stripAutoBaseFieldsFromEmptyBrochurePage = (page) => {
  if (!page?.elementLayout || !isEmptyPageContent(page.content) || Object.keys(page.customElements ?? {}).length) return;
  ['title', 'subtitle', 'meta', 'contact', 'extra'].forEach((id) => {
    delete page.elementLayout[id];
  });
};
const normalizeBrochurePages = (snapshot = state) => {
  if (!isBrochureDocument(snapshot)) return snapshot;

  const pages = Array.isArray(snapshot.pages) && snapshot.pages.length
    ? snapshot.pages
    : [{
        id: Reflect.get(snapshot, 'activePageId') ?? createPageId(),
        content: clonePlain(snapshot.content ?? initialDesignerState.content),
        elementLayout: clonePlain(snapshot.elementLayout ?? initialDesignerState.elementLayout),
        customElements: clonePlain(snapshot.customElements ?? {}),
      }];

  while (pages.length < 2) {
    pages.push(createBlankPage());
  }

  if (pages.length % 2 !== 0) {
    pages.push(createBlankPage());
  }

  snapshot.pages = pages;
  snapshot.pages.forEach((page, index) => {
    if (index > 0) {
      stripAutoBaseFieldsFromEmptyBrochurePage(page);
    }
  });
  Reflect.deleteProperty(snapshot, 'activePageId');

  return snapshot;
};
const ensureDocumentPages = (hydrateActivePage = false) => {
  if (!Array.isArray(state.pages) || !state.pages.length) {
    const firstId = activePageId.value ?? createPageId();
    activePageId.value = firstId;
    workingDocumentPageId.value = firstId;
    state.pages = [clonePageFromState(firstId), ...createBlankPages(minimumDocumentPageCount() - 1)];
    return;
  }

  state.pages = state.pages
    .filter((page) => page && typeof page === 'object')
    .map((page, index) => ({
      id: String(page.id ?? `page-${index + 1}`),
      content: clonePlain(page.content ?? initialDesignerState.content),
      elementLayout: clonePlain(page.elementLayout ?? initialDesignerState.elementLayout),
      customElements: clonePlain(page.customElements ?? {}),
    }));

  if (!state.pages.length) {
    const firstId = createPageId();
    activePageId.value = firstId;
    workingDocumentPageId.value = firstId;
    state.pages = [clonePageFromState(firstId), ...createBlankPages(minimumDocumentPageCount() - 1)];
  }

  normalizeBrochurePages(state);

  if (!activePageId.value || !state.pages.some((page) => page.id === activePageId.value)) {
    activePageId.value = state.pages[0].id;
  }
  if (!workingDocumentPageId.value || !state.pages.some((page) => page.id === workingDocumentPageId.value)) {
    workingDocumentPageId.value = activePageId.value;
  }

  const activePage = state.pages.find((page) => page.id === workingDocumentPageId.value);
  if (hydrateActivePage && activePage) {
    state.content = clonePlain(activePage.content);
    state.elementLayout = clonePlain(activePage.elementLayout);
    state.customElements = clonePlain(activePage.customElements);
  }
};
const syncActivePageSnapshot = () => {
  ensureDocumentPages();
  const activeIndex = state.pages.findIndex((page) => page.id === workingDocumentPageId.value);
  if (activeIndex === -1) return;
  state.pages[activeIndex] = clonePageFromState(workingDocumentPageId.value);
  refreshDocumentPageList();
};
const setVisualActiveDocumentPage = (pageId) => {
  if (!pageId) return;
  activePageId.value = pageId;
  visuallyFocusedPageId.value = pageId;
  linkedTextOverlayRevision.value += 1;
};
const switchToPage = async (pageId, { resetSelection = false } = {}) => {
  if (pageId === workingDocumentPageId.value) {
    setVisualActiveDocumentPage(pageId);
    return;
  }
  try {
    commitTextEdit({ recalculateHeight: false, reason: 'switch-page' });
  } catch (_) {
    // no-op
  }
  syncActivePageSnapshot();
  const target = state.pages.find((page) => page.id === pageId);
  if (!target) return;
  isSwitchingDocumentPage = true;
  activePageId.value = target.id;
  workingDocumentPageId.value = target.id;
  visuallyFocusedPageId.value = target.id;
  try {
    state.content = clonePlain(target.content);
    state.elementLayout = clonePlain(target.elementLayout);
    state.customElements = clonePlain(target.customElements);
    if (
      state.selectedElementId
      && state.selectedElementId !== 'background'
      && !state.elementLayout?.[state.selectedElementId]
    ) {
      state.selectedElementId = null;
      multiSelectionIds.value = [];
      selectedGroupId.value = null;
      editingElementId.value = null;
    }
    if (resetSelection) {
      state.selectedElementId = 'background';
      multiSelectionIds.value = [];
      selectedGroupId.value = null;
      editingElementId.value = null;
    }
    await nextTick();
  } finally {
    isSwitchingDocumentPage = false;
  }
  linkedTextOverlayRevision.value += 1;
  refreshDocumentPageList();
};
const setDocumentPageRef = (pageId, element) => {
  if (element) {
    documentPageRefs.set(pageId, element);
  } else {
    documentPageRefs.delete(pageId);
  }
};
const resolveMostVisiblePageId = () => {
  const firstNode = documentPageRefs.values().next().value;
  const scrollContainer = firstNode?.closest?.('.canvas-grid') ?? null;
  const viewport = scrollContainer?.getBoundingClientRect?.();
  if (!viewport) return null;

  const viewportHeight = viewport.height;
  const viewportCenter = viewport.top + viewportHeight / 2;
  let best = { id: null, score: Number.POSITIVE_INFINITY };

  documentPages.value.forEach((page) => {
    const node = documentPageRefs.get(page.id);
    const rect = node?.getBoundingClientRect?.();
    if (!rect) return;
    const visibleHeight = Math.max(0, Math.min(rect.bottom, viewport.bottom) - Math.max(rect.top, viewport.top));
    if (visibleHeight <= 0) return;
    const centerDistance = Math.abs((rect.top + rect.height / 2) - viewportCenter);
    if (centerDistance < best.score) {
      best = { id: page.id, score: centerDistance, visibleRatio: visibleHeight / rect.height };
    }
  });

  return best;
};
const updateVisuallyFocusedPage = () => {
  const mostVisible = resolveMostVisiblePageId();
  visuallyFocusedPageId.value = mostVisible?.id ?? activePageId.value;
  return mostVisible;
};
const activateVisibleDocumentPage = (mostVisible = resolveMostVisiblePageId(), { hydrate = true } = {}) => {
  if (!mostVisible?.id) return;
  if (!hydrate) {
    if (mostVisible.id !== activePageId.value) {
      setVisualActiveDocumentPage(mostVisible.id);
    }
    return;
  }
  if (mostVisible.id !== workingDocumentPageId.value || mostVisible.id !== activePageId.value) {
    switchToPage(mostVisible.id);
  }
};
const handleDocumentPagesScroll = () => {
  linkedTextOverlayRevision.value += 1;
  if (visiblePageFrame !== null) return;
  visiblePageFrame = requestAnimationFrame(() => {
    visiblePageFrame = null;
    const mostVisible = updateVisuallyFocusedPage();
    activateVisibleDocumentPage(mostVisible, { hydrate: false });
  });
};
const addDocumentPage = async ({ afterPageId = activePageId.value, duplicate = false } = {}) => {
  try {
    commitTextEdit();
  } catch (_) {
    // no-op
  }
  syncActivePageSnapshot();
  const source = duplicate
    ? clonePlain(state.pages.find((page) => page.id === afterPageId) ?? clonePageFromState())
    : createBlankPage();
  source.id = createPageId();
  const pagesToInsert = [source];
  if (isBrochureDocument()) {
    const extraPage = duplicate ? clonePlain(source) : createBlankPage();
    extraPage.id = createPageId();
    pagesToInsert.push(extraPage);
  }
  const insertAfterIndex = Math.max(0, state.pages.findIndex((page) => page.id === afterPageId));
  state.pages.splice(insertAfterIndex + 1, 0, ...pagesToInsert);
  refreshDocumentPageList();
  documentRevision.value += 1;
  await nextTick();
  flushDesignerStateWithThumbnail();
};
const duplicateDocumentPage = (pageId) => addDocumentPage({ afterPageId: pageId, duplicate: true });
const moveDocumentPage = async (pageId, direction) => {
  ensureDocumentPages();
  const currentIndex = state.pages.findIndex((page) => page.id === pageId);
  const nextIndex = currentIndex + direction;

  if (currentIndex === -1 || nextIndex < 0 || nextIndex >= state.pages.length) return;

  try {
    commitTextEdit();
  } catch (_) {
    // no-op
  }

  syncActivePageSnapshot();
  const [pageToMove] = state.pages.splice(currentIndex, 1);
  state.pages.splice(nextIndex, 0, pageToMove);
  refreshDocumentPageList();
  documentRevision.value += 1;
  await nextTick();
  flushDesignerStateWithThumbnail();
};
const deleteDocumentPage = async (pageId) => {
  ensureDocumentPages();
  if (state.pages.length <= minimumDocumentPageCount()) return;
  const pageIndex = state.pages.findIndex((page) => page.id === pageId);
  if (pageIndex === -1) return;

  try {
    commitTextEdit();
  } catch (_) {
    // no-op
  }

  if (state.pages.some((page) => page.id === workingDocumentPageId.value)) {
    syncActivePageSnapshot();
  }

  const deleteStart = isBrochureDocument() ? Math.floor(pageIndex / 2) * 2 : pageIndex;
  const deleteCount = isBrochureDocument() ? Math.min(2, state.pages.length - deleteStart) : 1;
  const deletedIds = state.pages.slice(deleteStart, deleteStart + deleteCount).map((page) => page.id);
  state.pages.splice(deleteStart, deleteCount);
  normalizeBrochurePages(state);
  const nextPage = state.pages[Math.min(deleteStart, state.pages.length - 1)] ?? state.pages[deleteStart - 1] ?? state.pages[0];
  if (!state.pages.length || !nextPage) return;

  if (deletedIds.includes(activePageId.value)) {
    activePageId.value = nextPage.id;
  }

  if (deletedIds.includes(workingDocumentPageId.value)) {
    workingDocumentPageId.value = nextPage.id;
    state.content = clonePlain(nextPage.content);
    state.elementLayout = clonePlain(nextPage.elementLayout);
    state.customElements = clonePlain(nextPage.customElements);
    state.selectedElementId = 'background';
    multiSelectionIds.value = [];
    selectedGroupId.value = null;
    editingElementId.value = null;
  }

  refreshDocumentPageList();
  documentRevision.value += 1;
  await nextTick();
  flushDesignerStateWithThumbnail();
};
ensureDocumentPages(true);
refreshDocumentPageList();
const pageIdFromPoint = (clientX, clientY) => {
  for (const [pageId] of documentPageRefs.entries()) {
    const rect = pageSurfaceRect(pageId);
    if (!rect) continue;
    if (clientX >= rect.left && clientX <= rect.right && clientY >= rect.top && clientY <= rect.bottom) {
      return pageId;
    }
  }
  return null;
};
const pageSurfaceRect = (pageId) => {
  const node = documentPageRefs.get(pageId);
  return node?.querySelector?.('[data-page-surface="true"], [data-editor-canvas="true"]')?.getBoundingClientRect?.() ?? null;
};
const boundsFromLayoutSnapshots = (snapshots) => {
  if (!snapshots.length) return null;

  const rects = snapshots.map(({ layout }) => ({
    x: Number(layout.x ?? 0),
    y: Number(layout.y ?? 0),
    w: Number(layout.w ?? 120),
    h: Number(layout.h ?? layout.fontSize ?? 44),
  }));
  const minX = Math.min(...rects.map((rect) => rect.x));
  const minY = Math.min(...rects.map((rect) => rect.y));
  const maxX = Math.max(...rects.map((rect) => rect.x + rect.w));
  const maxY = Math.max(...rects.map((rect) => rect.y + rect.h));

  return {
    x: minX,
    y: minY,
    w: maxX - minX,
    h: maxY - minY,
  };
};
const transferElementsToPage = async (elementIds, targetPageId, event, pointerOffset = null, sourceSnapshotsOverride = null) => {
  const ids = [...new Set(elementIds)].filter((id) => id && state.elementLayout[id]);
  if (!ids.length || !targetPageId || targetPageId === workingDocumentPageId.value) return false;

  const targetPage = state.pages.find((page) => page.id === targetPageId);
  if (!targetPage) return false;

  const sourceSnapshots = sourceSnapshotsOverride ?? ids.map((id) => ({
      id,
      layout: clonePlain(state.elementLayout[id]),
      customElement: clonePlain(state.customElements?.[id] ?? null),
    }));
  const bounds = boundsFromLayoutSnapshots(sourceSnapshots);
  const surfaceRect = pageSurfaceRect(targetPageId);

  targetPage.content = clonePlain(targetPage.content ?? initialDesignerState.content);
  targetPage.elementLayout = clonePlain(targetPage.elementLayout ?? createBlankElementLayout());
  targetPage.customElements = clonePlain(targetPage.customElements ?? {});

  let targetX = bounds?.x ?? 0;
  let targetY = bounds?.y ?? 0;
  if (surfaceRect && bounds) {
    targetX = Math.round(((event.clientX - surfaceRect.left) / (zoomScale.value || 1)) - (pointerOffset?.x ?? (bounds.w / 2)));
    targetY = Math.round(((event.clientY - surfaceRect.top) / (zoomScale.value || 1)) - (pointerOffset?.y ?? (bounds.h / 2)));
    if (!Number.isFinite(targetX)) targetX = bounds.x;
    if (!Number.isFinite(targetY)) targetY = bounds.y;
  }
  const dx = bounds ? targetX - bounds.x : 0;
  const dy = bounds ? targetY - bounds.y : 0;

  sourceSnapshots.forEach(({ id, layout, customElement }) => {
    delete state.elementLayout[id];
    delete state.customElements?.[id];

    const nextLayout = {
      ...layout,
      x: Math.round((layout.x ?? 0) + dx),
      y: Math.round((layout.y ?? 0) + dy),
    };
    targetPage.elementLayout[id] = nextLayout;
    if (customElement) {
      targetPage.customElements[id] = customElement;
    }
  });

  syncActivePageSnapshot();
  await switchToPage(targetPageId);
  if (ids.length === 1) {
    state.selectedElementId = ids[0];
    multiSelectionIds.value = [];
  } else {
    state.selectedElementId = null;
    multiSelectionIds.value = ids;
  }
  refreshDocumentPageList();
  flushDesignerStateWithThumbnail();
  return true;
};
const uploadEndpoint = computed(() => page.props.designer?.endpoints?.upload ?? '/designer/uploads');
const resetEndpoint = computed(() => page.props.designer?.endpoints?.reset ?? '/designer/state');
const designsStoreEndpoint = computed(() => page.props.designer?.endpoints?.designsStore ?? null);
const assetsIndexEndpoint = computed(() => page.props.designer?.endpoints?.assetsIndex ?? null);
const authUser = computed(() => page.props.auth?.user ?? null);
const persistedTemplates = computed(() => page.props.designer?.templates ?? []);
const currentDesignUuid = computed(() => state.currentDesignUuid ?? page.props.designer?.currentDesign?.uuid ?? null);
const currentDesignBaseTemplate = computed(() => (
  page.props.designer?.currentTemplate
  ?? page.props.designer?.currentDesign?.baseTemplate
  ?? null
));
const backendTemplateBaseMode = computed(() => Boolean(page.props.designer?.isTemplateBaseEditor));
const currentDesignDuplicateEndpoint = computed(() => state.currentDesignUuid ? `/designer/designs/${state.currentDesignUuid}/duplicate` : null);
const currentDesignRenameEndpoint = computed(() => state.currentDesignUuid ? `/designer/designs/${state.currentDesignUuid}/rename` : null);
const editableTemplates = computed(() => [
  ...(currentDesignBaseTemplate.value ? [currentDesignBaseTemplate.value] : []),
  ...adminTemplates.value,
  ...persistedTemplates.value.filter((template) => (
    template.uuid !== currentDesignBaseTemplate.value?.uuid
    && !adminTemplates.value.some((item) => item.uuid === template.uuid)
  )),
]);
const currentDesignTemplate = computed(() => editableTemplates.value.find((template) => (
  template.base_design_uuid === currentDesignUuid.value
  || template.uuid === state.selectedTemplateId
  || template.id === state.selectedTemplateId
)) ?? null);
const linkedFieldText = (fieldKey, fallback = '') => {
  if (!fieldKey) return fallback;
  if (fieldKey === 'meta') return metaLine.value;
  return state.content?.[fieldKey] ?? fallback;
};
const templateCategoryOptions = computed(() => {
  const seen = new Set(['general']);
  const options = [{ id: 'general', label: 'General' }];
  Object.entries(filterLabels)
    .filter(([id]) => id !== 'all')
    .forEach(([id, label]) => {
      if (seen.has(id)) return;
      seen.add(id);
      options.push({ id, label });
    });

  editableTemplates.value.forEach((template) => {
    (template.category_ids ?? []).forEach((id) => {
      if (!id || seen.has(id)) return;
      seen.add(id);
      options.push({ id, label: id });
    });
  });

  return options;
});
const templateObjectiveOptions = computed(() => {
  const seen = new Set(['generic']);
  const options = [{ id: 'generic', title: 'GenÃ©rico', description: 'Compatible con cualquier objetivo' }];
  objectiveOptions.forEach((objective) => {
    if (seen.has(objective.id)) return;
    seen.add(objective.id);
    options.push(objective);
  });
  editableTemplates.value.forEach((template) => {
    (template.objective_ids ?? []).forEach((id) => {
      if (!id || seen.has(id)) return;
      seen.add(id);
      options.push({ id, title: id, description: 'Objetivo personalizado' });
    });
  });

  return options;
});
const imageUploadProcessingConfig = computed(() => page.props.designer?.imageUploads ?? {
  maxWidth: 2400,
  maxHeight: 2400,
  jpegQuality: 95,
  webpQuality: 95,
});
const canvasRef = ref(null);
const zoomLevel = ref(100);
const imageInputRef = ref(null);
const imageUrlInput = ref('');
const imagePanelOpen = ref(false);
const imagePanelTab = ref('insert');
const shapePanelOpen = ref(false);
const textPanelOpen = ref(false);
const optionsPanelOpen = ref(true);
const shapeCategoryFilter = ref('all');
const elementMeasurements = reactive({});
const elementObservers = new Map();
const richEditorRefs = ref({});
const editingElementId = ref(null);
const editingBoxHeight = ref(null);
const activeLinkedTextBox = ref(null);
const selectedParagraphIndex = ref(0);
const paragraphSelection = reactive({ start: 0, end: 0, active: false });
const activePropertyPanel = ref(null);
const fileDragActive = ref(false);
const backgroundDropPreview = ref(false);
const templatePanelHover = ref(false);
let thumbnailTimer = null;
let pendingStateFlush = false;
let stateFlushRequestedDuringPending = false;
const toolbarPosition = reactive({ x: 0, y: 3 });
const toolbarDrag = reactive({ active: false, pointerId: null, startX: 0, startY: 0, originX: 0, originY: 0 });
const pinchPointers = new Map();
const pinchZoom = reactive({
  active: false,
  startDistance: 0,
  startZoom: 100,
  focusX: 0,
  focusY: 0,
});
const uploadProgressByAssetId = reactive({});
const activeUploadAssetIds = new Set();
const drag = reactive({
    active: false,
    mode: 'move',
    pointerId: null,
    elementId: null,
  groupId: null,
  groupSnapshot: null,
  multiSnapshot: null,
  handle: null,
  offsetX: 0,
  offsetY: 0,
  startClientX: 0,
  startClientY: 0,
  startX: 0,
  startY: 0,
  startW: 0,
  startH: 0,
  startRotation: 0,
  startAngle: 0,
  centerX: 0,
  centerY: 0,
  lastClientX: 0,
  lastClientY: 0,
  startFontSize: 0,
  startParagraphStyles: [],
});
const hoveredFieldKey = ref(null);
const touchIntent = reactive({
    pointerId: null,
    startX: 0,
    startY: 0,
});
const dragIntent = reactive({
  active: false,
  pointerId: null,
  elementId: null,
  groupId: null,
  targetType: 'element',
  startX: 0,
  startY: 0,
});
const linkedTextLink = reactive({
  active: false,
  sourceId: null,
  currentX: 0,
  currentY: 0,
  canvasX: 0,
  canvasY: 0,
  hoverTargetId: null,
});
const suppressElementClickUntil = ref(0);
const suppressCanvasClickUntil = ref(0);
const preserveEditorSelectionUntil = ref(0);
const multiSelectionIds = ref([]);
const marqueePreviewIds = ref([]);
const selectedGroupId = ref(null);
const groupedElements = reactive({});
const selectionMarquee = reactive({
  active: false,
  pointerId: null,
  dragged: false,
  startX: 0,
  startY: 0,
  currentX: 0,
  currentY: 0,
});

const colorOptions = [
  '#000000', '#545454', '#737373', '#a6a6a6', '#b4b4b4', '#d9d9d9', '#ffffff',
  '#ff3131', '#ff5757', '#ff66c4', '#e2a9f1', '#cb6ce6', '#8c52ff', '#5e17eb',
  '#0097b2', '#0cc0df', '#5ce1e6', '#38b6ff', '#5170ff', '#004aad', '#1800ad',
  '#00bf63', '#7ed957', '#c1ff72', '#ffde59', '#ffbd59', '#ff914d', '#ff751f',
];
const backgroundOptions = [
  'transparent',
  ...colorOptions,
];
const textEffectOptions = [
  { id: 'shadow1', label: 'Sombra 1' },
  { id: 'shadow2', label: 'Sombra 2' },
  { id: 'shadow', label: 'Sombreado' },
  { id: 'glow', label: 'Brillante' },
  { id: 'echo', label: 'Eco' },
  { id: 'outline', label: 'Contorno' },
  { id: 'background', label: 'Fondo' },
  { id: 'misaligned', label: 'Desalineado' },
  { id: 'hollow', label: 'Sin relleno' },
  { id: 'neon', label: 'Neon' },
  { id: 'distort', label: 'Distorsion' },
];
const textEffectCardFontFamily = '"Avenir Next", "Trebuchet MS", "Segoe UI", sans-serif';
const BASE_CANVAS_SHORT_SIDE = 368;
const BASE_CANVAS_LONG_SIDE = 620;
const shapeGradientOptions = [
  { id: 'g1', start: '#0ea5e9', end: '#8b5cf6' },
  { id: 'g2', start: '#22c55e', end: '#0ea5e9' },
  { id: 'g3', start: '#f59e0b', end: '#ef4444' },
  { id: 'g4', start: '#f43f5e', end: '#8b5cf6' },
  { id: 'g5', start: '#14b8a6', end: '#22c55e' },
  { id: 'g6', start: '#111827', end: '#6366f1' },
  { id: 'g7', start: '#67e8f9', end: '#7c3aed' },
  { id: 'g8', start: '#fde68a', end: '#f43f5e' },
  { id: 'g9', start: '#1d4ed8', end: '#06b6d4' },
  { id: 'g10', start: '#7c2d12', end: '#f97316' },
  { id: 'g11', start: '#be123c', end: '#fb7185' },
  { id: 'g12', start: '#166534', end: '#86efac' },
];
const shapeGradientDirections = [
  { value: 0, label: 'Arriba â†’ abajo', icon: 'ph:arrow-down' },
  { value: 90, label: 'Izquierda â†’ derecha', icon: 'ph:arrow-right' },
  { value: 135, label: 'Diagonal â†˜', icon: 'ph:arrow-down-right' },
  { value: 45, label: 'Diagonal â†—', icon: 'ph:arrow-up-right' },
  { value: 180, label: 'Abajo â†’ arriba', icon: 'ph:arrow-up' },
  { value: 270, label: 'Derecha â†’ izquierda', icon: 'ph:arrow-left' },
];
const normalizeHexCandidate = (value) => {
  if (typeof value !== 'string') return null;
  const trimmed = value.trim();
  if (trimmed === 'transparent') return null;
  if (/^#[\da-f]{6}$/i.test(trimmed)) return trimmed.toLowerCase();
  if (/^#[\da-f]{3}$/i.test(trimmed)) {
    return `#${trimmed[1]}${trimmed[1]}${trimmed[2]}${trimmed[2]}${trimmed[3]}${trimmed[3]}`.toLowerCase();
  }
  return null;
};
const fontOptions = (page.props.fontFamilies ?? []).map(f => ({
  label: f,
  family: f,
}));
const textPropertyTabs = [
    { id: 'typography', label: 'Tipografía' , class: 'order-first text-xl border-1 border-gray-500'},
    // { id: 'color', label: 'A', labelClass:'text-shadow-xs text-xl border-b-3',class: '' },
    { id: 'fontSize', icon: 'radix-icons:font-size', label: 'Tamaño', title: 'Tamaño', class: 'order-first md:hidden' },
    { id: 'format', icon: 'mdi:format-text', label: 'Formato', title: 'Formato', class: 'order-last md:hidden' },
    { id: 'spacing', icon: 'mdi:format-line-spacing', title: 'Interlineado y espaciado', class: 'order-last' },
    { id: 'opacity', icon: 'carbon:opacity', class: 'order-last', iconClass: 'text-3xl' },
    { id: 'effects', label: 'Efectos', class: 'order-last' },
    { id: 'arrange', label: 'Posición' , class: 'order-last'},
];
const imagePropertyTabs = [
  { id: 'color', icon: 'mdi:palette-outline', label: 'Color', class: 'order-first' },
  { id: 'border', icon: 'radix-icons:border-width', title: 'Borde', class: 'order-first' },
  { id: 'roundness', icon: 'mdi:rounded-corner', title: 'Redondez', class: 'order-first' },
  { id: 'crop', icon: 'ph:crop-bold', title: 'Recortar', class: 'order-last' },
  { id: 'rotate', icon: '', label: 'Girar', class: 'order-last' },
  { id: 'opacity', icon: 'carbon:opacity', class: 'order-last' },
  { id: 'effects', label: 'Efectos', class: 'order-last' },
  { id: 'arrange', label: 'Posición', class: 'order-last' },
  { id: 'set-as-background', icon: 'tabler:background', title: 'Fijar como fondo', class: 'order-last' },
];
const shapePropertyTabs = [
  { id: 'color', icon: 'mdi:palette-outline', label: 'Color', class: 'order-first' },
  { id: 'border', icon: 'radix-icons:border-width', title: 'Borde', class: 'order-first' },
  { id: 'opacity', icon: 'carbon:opacity', class: 'order-last' },
  { id: 'effects', label: 'Efectos', class: 'order-last' },
  { id: 'arrange', label: 'Posición', class: 'order-last' },
];
const backgroundPropertyTabs = [
  { id: 'color', icon: 'mdi:palette-outline', label: 'Color', class: 'order-first' },
];

const baseTextElementIds = new Set(['title', 'subtitle', 'meta', 'contact', 'extra']);
const textPresets = [
  {
    id: 'heading',
    label: 'Título',
    preview: 'Agrega un titulo',
    fontSize: 52,
    fontWeight: 'bold',
    lineHeight: 1,
    width: 320,
  },
  {
    id: 'medium',
    label: 'Subtítulo',
    preview: 'Agrega un subtitulo',
    fontSize: 28,
    fontWeight: 'bold',
    lineHeight: 1.2,
    width: 300,
  },
  {
    id: 'normal',
    label: 'Texto normal',
    preview: 'Escribe tu texto aqui',
    fontSize: 18,
    fontWeight: 'regular',
    lineHeight: 1.4,
    width: 280,
  },
];
const shapeCategories = [
  {
    id: 'basicas',
    label: 'Básicas',
    shapes: [
      { id: 'rectangle', label: 'Rectángulo' },
      { id: 'rectangle-outline', label: 'Rectángulo recto' },
      { id: 'circle', label: 'Círculo' },
      { id: 'triangle-up', label: 'Triángulo' },
      { id: 'triangle-right-angle', label: 'Triángulo rectángulo' },
      { id: 'parallelogram', label: 'Paralelogramo' },
      { id: 'trapezoid', label: 'Trapecio' },
    ],
  },
  {
    id: 'poligonos',
    label: 'Polígonos',
    shapes: [
      { id: 'pentagon', label: 'Pentágono' },
      { id: 'hexagon', label: 'Hexágono' },
      { id: 'octagon', label: 'Octágono' },
    ],
  },
  {
    id: 'estrellas',
    label: 'Estrellas',
    shapes: [
      { id: 'star-5', label: 'Estrella 5' },
      { id: 'star-4', label: 'Estrella 4' },
      { id: 'star-6', label: 'Estrella 6' },
      { id: 'star-burst', label: 'Destello' },
    ],
  },
  {
    id: 'flechas',
    label: 'Flechas',
    shapes: [
      { id: 'arrow-right', label: 'Flecha â†’' },
      { id: 'arrow-curved', label: 'Flecha curva' },
      { id: 'arrow-double-h', label: 'Doble H' },
      { id: 'chevron-right', label: 'Chevron â†’' },
    ],
  },
  {
    id: 'bocadillos',
    label: 'Bocadillos',
    shapes: [
      { id: 'callout', label: 'Bocadillo clásico' },
      { id: 'callout-ellipse', label: 'Bocadillo elipse' },
      { id: 'callout-cloud', label: 'Bocadillo nube' },
      { id: 'callout-burst', label: 'Bocadillo explosión' },
    ],
  },
  {
    id: 'marcos',
    label: 'Marcos',
    shapes: [
      { id: 'frame', label: 'Marco clásico' },
      { id: 'frame-rounded', label: 'Marco redondeado' },
      { id: 'frame-thick', label: 'Marco grueso' },
      { id: 'frame-thin', label: 'Marco fino' },
    ],
  },
  {
    id: 'especiales',
    label: 'Especiales',
    shapes: [
      { id: 'cross', label: 'Cruz' },
      { id: 'x-mark', label: 'Aspa' },
      { id: 'heart', label: 'Corazón' },
      { id: 'badge', label: 'Escudo' },
      { id: 'ribbon', label: 'Cinta' },
    ],
  },
];
// Lookup plano de todas las figuras
const shapePresets = shapeCategories.flatMap((cat) => cat.shapes.map((s) => ({ ...s, category: cat.id })));

const imagePanelTabs = [
  { id: 'insert', label: 'Insertar' },
  { id: 'library', label: 'Libreria' },
  { id: 'uploads', label: 'Subidas' },
];
const imageLibrary = [
  { id: 'lib-1', src: 'https://picsum.photos/seed/tseyor1/900/600', label: 'Biblioteca 1' },
  { id: 'lib-2', src: 'https://picsum.photos/seed/tseyor2/900/600', label: 'Biblioteca 2' },
  { id: 'lib-3', src: 'https://picsum.photos/seed/tseyor3/900/600', label: 'Biblioteca 3' },
  { id: 'lib-4', src: 'https://picsum.photos/seed/tseyor4/900/600', label: 'Biblioteca 4' },
  { id: 'lib-5', src: 'https://picsum.photos/seed/tseyor5/900/600', label: 'Biblioteca 5' },
  { id: 'lib-6', src: 'https://picsum.photos/seed/tseyor6/900/600', label: 'Biblioteca 6' },
];

const baseElementLabels = {
  background: 'fondo',
  title: 'titulo',
  subtitle: 'subtitulo',
  meta: 'fecha y hora',
  contact: 'contacto',
  extra: 'texto adicional',
};

const contentFieldLabels = {
  title: 'titulo',
  subtitle: 'subtitulo',
  date: 'fecha',
  time: 'hora',
  location: 'ubicacion',
  platform: 'plataforma',
  teacher: 'ponente',
  price: 'precio',
  contact: 'contacto',
  extra: 'texto adicional',
};

const {
  historyApplying,
  canUndo,
  canRedo,
  undoActionLabel,
  redoActionLabel,
  pushHistorySnapshot,
  scheduleHistorySnapshot,
  performUndo,
  performRedo,
  replaceImageAssetSource,
  mutateWithoutHistory,
} = useEditorHistory({
  state,
  editingElementId,
  commitTextEdit: (...args) => commitTextEdit(...args),
  clearSelection: () => clearSelection(),
  baseElementLabels,
  contentFieldLabels,
});

const metaLine = computed(() => [state.content.date, state.content.time].filter(Boolean).join(' Â· '));
const isTemplateBaseEditor = computed(() => Boolean(
  backendTemplateBaseMode.value
  || currentDesignBaseTemplate.value?.base_design_uuid === currentDesignUuid.value
  || currentDesignTemplate.value?.base_design_uuid === currentDesignUuid.value
));
const templateFieldLabels = {
  title: 'Título',
  subtitle: 'Subtítulo',
  meta: 'Fecha / hora',
  date: 'Fecha',
  time: 'Hora',
  location: 'Lugar',
  platform: 'URL / acceso',
  teacher: 'Profesor',
  price: 'Precio',
  contact: 'Contacto',
  extra: 'Texto adicional',
};
const coreTemplateFieldDefinitions = [
  { id: 'title', key: 'title', label: 'Título', type: 'text', description: 'Campo principal del diseño.' },
  { id: 'subtitle', key: 'subtitle', label: 'Subtítulo', type: 'text', description: 'Texto secundario o claim.' },
  { id: 'meta', key: 'meta', label: 'Fecha / hora', type: 'text', description: 'Campo combinado de fecha y hora del diseño.' },
  { id: 'contact', key: 'contact', label: 'Contacto', type: 'text', description: 'Información de contacto o inscripción.' },
  { id: 'extra', key: 'extra', label: 'Texto adicional', type: 'textarea', description: 'Notas, requisitos o información complementaria.' },
];
const normalizeTemplateFieldDefinition = (field) => {
  const id = field?.id ?? field?.key;
  if (!id) return null;

  return {
    ...field,
    id,
    key: field.key ?? id,
    label: field.label ?? templateFieldLabels[id] ?? id,
    description: field.description ?? field.helper ?? null,
  };
};
const templateFieldDefinitions = computed(() => {
  const currentFields = (objectiveRecommendations[state.objective] ?? objectiveRecommendations.generic).fields ?? [];
  const allRecommendedFields = Object.values(objectiveRecommendations)
    .flatMap((recommendation) => recommendation.fields ?? []);
  const merged = new Map();

  [
    ...coreTemplateFieldDefinitions,
    ...currentFields,
    ...allRecommendedFields,
  ].forEach((field) => {
    const normalized = normalizeTemplateFieldDefinition(field);
    if (!normalized || merged.has(normalized.id)) return;
    merged.set(normalized.id, normalized);
  });

  return Array.from(merged.values());
});
const templateFieldDefaultTexts = {
  title: 'Título de prueba',
  subtitle: 'Subtítulo de prueba',
  date: 'Fecha de prueba',
  time: 'Hora de prueba',
  location: 'Lugar de prueba',
  platform: 'URL de prueba',
  teacher: 'Profesor de prueba',
  price: 'Precio de prueba',
  contact: 'Contacto de prueba',
  extra: 'Texto adicional de prueba',
  meta: 'Fecha de prueba Â· Hora de prueba',
};
const templateContentFieldIds = new Set(['title', 'subtitle', 'contact', 'extra']);
const normalizePlainTextValue = (value) => String(value ?? '')
  .replace(/<[^>]*>/g, '')
  .replace(/&nbsp;/gi, ' ')
  .replace(/Â /g, ' ')
  .trim();
const hasMeaningfulText = (value) => normalizePlainTextValue(value).length > 0;

const templateFieldUsage = computed(() => Object.fromEntries(
  templateFieldDefinitions.value.map((field) => [field.id, Boolean(state.elementLayout?.[field.id])]),
));
const linkedTextLayoutFromAnyPage = (id) => {
  if (state.elementLayout?.[id]) return state.elementLayout[id];
  for (const page of state.pages) {
    if (page.elementLayout?.[id]) return page.elementLayout[id];
  }
  return null;
};

const linkedTextElementFromAnyPage = (id) => {
  if (state.customElements?.[id]) return state.customElements[id];
  for (const page of state.pages) {
    if (page.customElements?.[id]) return page.customElements[id];
  }
  return null;
};

const elementPageIdFromAnyPage = (id) => {
  if (!id) return null;
  if (state.elementLayout?.[id] || state.customElements?.[id]) return workingDocumentPageId.value;
  for (const page of state.pages ?? []) {
    if (page.elementLayout?.[id] || page.customElements?.[id]) return page.id;
  }
  return null;
};
const rotateCanvasPoint = (x, y, cx, cy, angleDeg = 0) => {
  if (!angleDeg) return { x, y };
  const angleRad = (angleDeg * Math.PI) / 180;
  const dx = x - cx;
  const dy = y - cy;
  const cos = Math.cos(angleRad);
  const sin = Math.sin(angleRad);
  return {
    x: cx + dx * cos - dy * sin,
    y: cy + dx * sin + dy * cos,
  };
};

const linkedTextSetLayoutField = (id, field, value) => {
  if (state.elementLayout?.[id]) {
    state.elementLayout[id][field] = value;
    return;
  }
  for (const page of state.pages) {
    if (page.elementLayout?.[id]) {
      page.elementLayout[id][field] = value;
      return;
    }
  }
};

const linkedTextSetElementField = (id, field, value) => {
  if (state.customElements?.[id]) {
    state.customElements[id][field] = value;
    return;
  }
  for (const page of state.pages) {
    if (page.customElements?.[id]) {
      page.customElements[id][field] = value;
      return;
    }
  }
};

const getLinkedTextChain = (startId) => {
  const chain = [];
  let currentId = startId;
  const visited = new Set();
  while (currentId && !visited.has(currentId)) {
    visited.add(currentId);
    const layout = linkedTextLayoutFromAnyPage(currentId);
    if (!layout) break;
    chain.push({ id: currentId, layout });
    currentId = layout.linkedTextNext;
  }
  return chain;
};

const getLinkedTextChainHead = (startId) => {
  let currentId = startId;
  const visited = new Set();
  while (currentId && !visited.has(currentId)) {
    visited.add(currentId);
    const layout = linkedTextLayoutFromAnyPage(currentId);
    if (!layout) break;
    if (layout.linkedTextPrev) {
      currentId = layout.linkedTextPrev;
    } else {
      return currentId;
    }
  }
  return startId;
};

const linkedTextOverlayPoint = (boxId, anchor = 'source') => {
  linkedTextOverlayRevision.value;
  const pageId = elementPageIdFromAnyPage(boxId);
  const layout = linkedTextLayoutFromAnyPage(boxId);
  const pageNode = pageId ? documentPageRefs.get(pageId) : null;
  const surface = pageNode?.querySelector?.('[data-page-surface="true"], [data-editor-canvas="true"]') ?? null;
  const scroll = canvasGridRef.value;
  if (!layout || !surface || !scroll) return null;

  const surfaceRect = surface.getBoundingClientRect();
  const scrollRect = scroll.getBoundingClientRect();
  const surfaceLeft = surfaceRect.left - scrollRect.left + scroll.scrollLeft;
  const surfaceTop = surfaceRect.top - scrollRect.top + scroll.scrollTop;
  const fin = (value, fallback) => Number.isFinite(value) ? value : fallback;
  const bw = 24;
  const bh = 24;
  const offset = anchor === 'source' ? 4 : 0;
  const localX = anchor === 'source'
    ? fin(layout.x, 0) + fin(layout.w, 300) - offset - bw / 2
    : fin(layout.x, 0);
  const localY = anchor === 'source'
    ? fin(layout.y, 0) + fin(layout.h, 120) - offset - bh / 2
    : fin(layout.y, 0);
  const cx = fin(layout.x, 0) + fin(layout.w, 300) / 2;
  const cy = fin(layout.y, 0) + fin(layout.h, 120) / 2;
  const rotated = rotateCanvasPoint(localX, localY, cx, cy, fin(layout.rotation, 0));
  return {
    x: surfaceLeft + rotated.x,
    y: surfaceTop + rotated.y,
  };
};

const linkedTextGlobalLinkLines = computed(() => {
  linkedTextOverlayRevision.value;
  const selectedId = state.selectedElementId;
  const selectedElement = linkedTextElementFromAnyPage(selectedId);
  if (!selectedId || selectedElement?.type !== 'linkedText') return [];

  const headId = getLinkedTextChainHead(selectedId);
  const chain = getLinkedTextChain(headId);
  const lines = [];
  for (let index = 0; index < chain.length - 1; index += 1) {
    const source = linkedTextOverlayPoint(chain[index].id, 'source');
    const target = linkedTextOverlayPoint(chain[index + 1].id, 'target');
    if (source && target) {
      lines.push({ x1: source.x, y1: source.y, x2: target.x, y2: target.y });
    }
  }
  return lines;
});

const linkedTextOverlayStyle = computed(() => {
  linkedTextOverlayRevision.value;
  const grid = canvasGridRef.value;
  return {
    width: `${grid?.scrollWidth ?? 0}px`,
    height: `${grid?.scrollHeight ?? 0}px`,
  };
});

const getLinkedTextStyleSourceId = (id) => {
  if (linkedTextElementFromAnyPage(id)?.type !== 'linkedText') return id;
  return getLinkedTextChainHead(id);
};

const recalculateLinkedTextAllocations = (headId) => {
  const chain = getLinkedTextChain(headId);
  if (chain.length === 0) return;

  const headElement = linkedTextElementFromAnyPage(headId);
  if (!headElement || headElement.type !== 'linkedText') return;

  const fullHtml = headElement.html || headElement.text || '';
  const groupId = linkedTextLayoutFromAnyPage(headId)?.linkedTextGroupId;
  if (!groupId) return;

  const chainLayouts = chain.map((item) => {
    const l = linkedTextLayoutFromAnyPage(item.id) || {};
    const styleSourceLayout = linkedTextLayoutFromAnyPage(getLinkedTextStyleSourceId(item.id)) || l;
    return {
      id: item.id,
      w: l.w || 300,
      h: l.h || 120,
      fontSize: styleSourceLayout.fontSize || l.fontSize || 18,
      fontFamily: styleSourceLayout.fontFamily || l.fontFamily || 'Poppins, sans-serif',
      fontWeight: styleSourceLayout.fontWeight || l.fontWeight || 'regular',
      italic: styleSourceLayout.italic ?? l.italic ?? false,
      underline: styleSourceLayout.underline ?? l.underline ?? false,
      uppercase: styleSourceLayout.uppercase ?? l.uppercase ?? false,
      textAlign: styleSourceLayout.textAlign || l.textAlign || 'left',
      color: styleSourceLayout.color || l.color || '#ffffff',
      letterSpacing: styleSourceLayout.letterSpacing ?? l.letterSpacing ?? 0,
      lineHeight: styleSourceLayout.lineHeight || l.lineHeight || 1.4,
      paragraphStyles: Array.isArray(styleSourceLayout.paragraphStyles)
        ? styleSourceLayout.paragraphStyles.map((style) => ({ ...style }))
        : [],
      linkedTextNext: l.linkedTextNext || null,
    };
  });

  const firstLayout = chainLayouts[0] || {};
  const containerStyle = {
    fontSize: firstLayout.fontSize || 18,
    fontFamily: firstLayout.fontFamily || 'Poppins, sans-serif',
    lineHeight: firstLayout.lineHeight || 1.4,
    letterSpacing: firstLayout.letterSpacing || 0,
  };

  // Log antes de redistribuir
  frontendLog.info('redistribution',
    `Redistribuyendo texto enlazado para grupo ${groupId}`,
    {
      headId,
      groupId,
      chainLength: chain.length,
      chainIds: chain.map(item => item.id),
      fullHtmlLength: fullHtml.length,
      fullHtmlPreview: fullHtml.substring(0, 200),
      chainLayouts,
      containerStyle,
    }
  );

  linkedTextBoxSystem.redistribute(groupId, fullHtml, chainLayouts, containerStyle);

  // Log despuÃ©s de redistribuir - registrar fragmentos
  const system = linkedTextBoxSystem.getOrCreateSystem(groupId);
  if (system.fragments) {
    for (const [boxId, fragment] of Object.entries(system.fragments)) {
      frontendLog.logFragmentation(groupId, boxId, fragment);
    }
  }
};

  const getLinkedTextBoxText = (boxId) => {
    const layout = linkedTextLayoutFromAnyPage(boxId);
    if (!layout?.linkedTextGroupId) return { text: '', displayHtml: '', overflowHtml: '', fullTextHtml: '', tailHtml: '', prefixHtml: '', editorTopOffset: 0, editorTextOffset: 0, fitsInBox: true };

    const groupId = layout.linkedTextGroupId;
    const headId = getLinkedTextChainHead(boxId);

    // Asegurar que el sistema tiene los fragmentos calculados
    const system = linkedTextBoxSystem.getOrCreateSystem(groupId);
    if (!system.fragments || Object.keys(system.fragments).length === 0) {
      recalculateLinkedTextAllocations(headId);
    }

    // Determinar si es la Ãºltima caja de la cadena
    const chain = getLinkedTextChain(headId);
    const isLastInChain = chain.length > 0 && chain[chain.length - 1].id === boxId;

    const hasFragment = Boolean(system.fragments && Object.prototype.hasOwnProperty.call(system.fragments, boxId));
    const fragment = linkedTextBoxSystem.getFragmentForBox(groupId, boxId);

    // Si todavía no hay fragmento, usar el texto del elemento head directamente
    if (!hasFragment) {
      const headElement = linkedTextElementFromAnyPage(headId);
      const rawText = headElement?.text || '';
      return {
        text: rawText,
        displayHtml: rawText ? `<p>${rawText}</p>` : '',
        overflowHtml: '',
        fullTextHtml: rawText ? `<p>${rawText}</p>` : '',
        tailHtml: rawText ? `<p>${rawText}</p>` : '',
        prefixHtml: '',
        editorTopOffset: 0,
        editorTextOffset: 0,
        fitsInBox: true,
        isLastInChain
      };
    }

    // Solo mostrar overflow en la Ãºltima caja de la cadena
    const overflowHtml = isLastInChain ? (fragment.overflowHtml || '') : '';

    const chainIndex = chain.findIndex((item) => item.id === boxId);
    const fallbackEditorTopOffset = chainIndex > 0
      ? chain.slice(0, chainIndex).reduce((total, item) => total + Number(item.layout?.h || 0), 0)
      : 0;

    return {
      text: fragment.html ? fragment.html.replace(/<[^>]*>/g, '') : '',
      displayHtml: fragment.html || '',
      overflowHtml,
      fullTextHtml: fragment.fullTextHtml || '',
      tailHtml: fragment.tailHtml || '',
      prefixHtml: fragment.prefixHtml || '',
      editorTopOffset: fragment.editorTopOffset || fallbackEditorTopOffset || 0,
      editorTextOffset: fragment.editorTextOffset || 0,
      fitsInBox: fragment.fitsInBox ?? true,
      isLastInChain
    };
  };

const editorElements = computed(() => {
  const baseTextElements = [
    { id: 'title', type: 'text', label: 'Titulo', fieldKey: 'title', text: state.content.title },
    { id: 'subtitle', type: 'text', label: 'Subtitulo', fieldKey: 'subtitle', text: state.content.subtitle },
    { id: 'meta', type: 'text', label: 'Fecha / hora', fieldKey: 'meta', text: metaLine.value },
    { id: 'contact', type: 'text', label: 'Contacto', fieldKey: 'contact', text: state.content.contact },
    { id: 'extra', type: 'text', label: 'Texto adicional', fieldKey: 'extra', text: state.content.extra },
  ];
  const customElements = Object.entries(state.customElements ?? {}).map(([id, element]) => {
    const isBeingEdited = editingElementId.value === id;
    const linkedTextBoxData = element.type === 'linkedText' ? getLinkedTextBoxText(id) : null;
    const linkedTextStyleSourceId = element.type === 'linkedText' ? getLinkedTextStyleSourceId(id) : id;
    const linkedTextStyleSourceLayout = linkedTextLayoutFromAnyPage(linkedTextStyleSourceId) ?? null;

    // Regla 3: Si está en edición, el texto debe ser el COMPLETO (del head), no el fragmento
    let elementText;
    if (element.type === 'text') {
      elementText = linkedFieldText(element.fieldKey, element.text ?? '');
    } else if (element.type === 'linkedText') {
      if (isBeingEdited) {
        // En edición: usar el texto completo del head
        const headId = getLinkedTextChainHead(id);
        const headElement = state.customElements[headId];
        elementText = headElement?.text ?? '';
      } else {
        // En display: usar el fragmento
        elementText = linkedTextBoxData?.text ?? '';
      }
    } else {
      elementText = '';
    }

    return {
      id,
      type: element.type,
      label: element.label ?? 'Elemento',
      fieldKey: element.fieldKey ?? null,
      text: elementText,
      linkedTextStyleSourceId,
      linkedTextParagraphStyles: element.type === 'linkedText'
        ? (linkedTextStyleSourceLayout?.paragraphStyles ?? [])
        : null,
      linkedTextDisplayHtml: element.type === 'linkedText' ? (linkedTextBoxData?.displayHtml ?? '') : '',
      linkedTextOverflowHtml: element.type === 'linkedText' ? (linkedTextBoxData?.overflowHtml ?? '') : '',
      linkedTextFullTextHtml: element.type === 'linkedText' ? (linkedTextBoxData?.fullTextHtml ?? '') : '',
      linkedTextTailHtml: element.type === 'linkedText' ? (linkedTextBoxData?.tailHtml ?? '') : '',
      linkedTextInitialHtml: element.type === 'linkedText' && isBeingEdited ? (linkedTextBoxData?.tailHtml ?? '') : '',
      linkedTextEditorTopOffset: element.type === 'linkedText' ? (linkedTextBoxData?.editorTopOffset ?? 0) : 0,
      linkedTextEditorTextOffset: element.type === 'linkedText' ? (linkedTextBoxData?.editorTextOffset ?? 0) : 0,
      linkedTextIsLastInChain: element.type === 'linkedText' ? (linkedTextBoxData?.isLastInChain ?? false) : false,
      src: element.type === 'image' ? element.src : null,
      shapeKind: element.type === 'shape' ? element.shapeKind : null,
    };
  });

  return [...baseTextElements, ...customElements]
    .filter((item) => state.elementLayout[item.id])
    .sort((a, b) => (state.elementLayout[a.id]?.zIndex ?? 0) - (state.elementLayout[b.id]?.zIndex ?? 0));
});
const documentPages = computed(() => {
  documentRevision.value;
  return documentPageList.value;
});
const hasMultiplePages = computed(() => documentPages.value.length > 1);
const canDeleteDocumentPage = computed(() => documentPages.value.length > minimumDocumentPageCount());
const physicalPageLabel = (pageIndex) => (
  isBrochureDocument()
    ? `Página física ${pageIndex + 1} Â· folleto ${brochurePagePairForPhysicalPage(pageIndex, documentPages.value.length).join('-')}`
    : `Página ${pageIndex + 1}`
);
const brochurePanelLabels = (pageIndex) => brochurePagePairForPhysicalPage(pageIndex, documentPages.value.length)
  .map((pageNumber) => `Página de folleto ${pageNumber}`);
const addPageButtonLabel = computed(() => (
  isBrochureDocument()
    ? '+ Añadir 2 páginas físicas (4 páginas de folleto)'
    : '+ Añadir una página'
));
const deletePageTip = computed(() => (
  isBrochureDocument()
    ? 'Eliminar este pliego (2 páginas físicas)'
    : 'Eliminar página'
));
const pageMetaLine = (content = {}) => [content.date, content.time].filter(Boolean).join(' · ');
const linkedPageFieldText = (content = {}, fieldKey, fallback = '') => {
  if (!fieldKey) return fallback;
  if (fieldKey === 'meta') return pageMetaLine(content);
  return content?.[fieldKey] ?? fallback;
};
const renderPageState = (pageState) => (
  pageState?.id === workingDocumentPageId.value
    ? {
        ...pageState,
        content: state.content,
        elementLayout: state.elementLayout,
        customElements: state.customElements,
      }
    : pageState
);
const stageStateForPage = (pageState) => {
  if (pageState?.id === workingDocumentPageId.value) return state;
  const renderState = renderPageState(pageState);
  return {
    ...state,
    content: renderState?.content ?? {},
    elementLayout: renderState?.elementLayout ?? {},
    customElements: renderState?.customElements ?? {},
    selectedElementId: null,
  };
};
const editorElementsForPage = (pageState) => {
  const renderState = renderPageState(pageState);
  const content = renderState?.content ?? {};
  const layout = renderState?.elementLayout ?? {};
  const custom = renderState?.customElements ?? {};
  const baseTextElements = [
    { id: 'title', type: 'text', label: 'Titulo', fieldKey: 'title', text: content.title },
    { id: 'subtitle', type: 'text', label: 'Subtitulo', fieldKey: 'subtitle', text: content.subtitle },
    { id: 'meta', type: 'text', label: 'Fecha / hora', fieldKey: 'meta', text: pageMetaLine(content) },
    { id: 'contact', type: 'text', label: 'Contacto', fieldKey: 'contact', text: content.contact },
    { id: 'extra', type: 'text', label: 'Texto adicional', fieldKey: 'extra', text: content.extra },
  ];

  const customElements = Object.entries(custom).map(([id, element]) => {
    const isBeingEdited = renderState?.id === workingDocumentPageId.value && editingElementId.value === id;
    const linkedTextBoxData = element.type === 'linkedText' ? getLinkedTextBoxText(id) : null;
    const linkedTextStyleSourceId = element.type === 'linkedText' ? getLinkedTextStyleSourceId(id) : id;
    const linkedTextStyleSourceLayout = linkedTextLayoutFromAnyPage(linkedTextStyleSourceId) ?? layout[linkedTextStyleSourceId] ?? null;

    let elementText;
    if (element.type === 'text') {
      elementText = linkedPageFieldText(content, element.fieldKey, element.text ?? '');
    } else if (element.type === 'linkedText') {
      if (isBeingEdited) {
        const headId = getLinkedTextChainHead(id);
        const headElement = linkedTextElementFromAnyPage(headId);
        elementText = headElement?.text ?? '';
      } else {
        elementText = linkedTextBoxData?.text ?? '';
      }
    } else {
      elementText = '';
    }

    return {
      id,
      type: element.type,
      label: element.label ?? 'Elemento',
      fieldKey: element.fieldKey ?? null,
      text: elementText,
      linkedTextStyleSourceId,
      linkedTextParagraphStyles: element.type === 'linkedText'
        ? (linkedTextStyleSourceLayout?.paragraphStyles ?? [])
        : null,
      linkedTextDisplayHtml: element.type === 'linkedText' ? (linkedTextBoxData?.displayHtml ?? '') : '',
      linkedTextOverflowHtml: element.type === 'linkedText' ? (linkedTextBoxData?.overflowHtml ?? '') : '',
      linkedTextFullTextHtml: element.type === 'linkedText' ? (linkedTextBoxData?.fullTextHtml ?? '') : '',
      linkedTextTailHtml: element.type === 'linkedText' ? (linkedTextBoxData?.tailHtml ?? '') : '',
      linkedTextInitialHtml: element.type === 'linkedText' && isBeingEdited ? (linkedTextBoxData?.tailHtml ?? '') : '',
      linkedTextEditorTopOffset: element.type === 'linkedText' ? (linkedTextBoxData?.editorTopOffset ?? 0) : 0,
      linkedTextEditorTextOffset: element.type === 'linkedText' ? (linkedTextBoxData?.editorTextOffset ?? 0) : 0,
      linkedTextIsLastInChain: element.type === 'linkedText' ? (linkedTextBoxData?.isLastInChain ?? false) : false,
      src: element.type === 'image' ? element.src : null,
      shapeKind: element.type === 'shape' ? element.shapeKind : null,
    };
  });

  return [...baseTextElements, ...customElements]
    .filter((item) => layout[item.id])
    .sort((a, b) => (layout[a.id]?.zIndex ?? 0) - (layout[b.id]?.zIndex ?? 0));
};
const isPageTextElement = (pageState, id) => {
  const renderState = renderPageState(pageState);
  if (baseTextElementIds.has(id)) return true;
  const type = renderState?.customElements?.[id]?.type;
  return type === 'text' || type === 'linkedText';
};
const isPageLinkedTextElement = (pageState, id) => renderPageState(pageState)?.customElements?.[id]?.type === 'linkedText';
const pageElementBoxStyle = (pageState, id) => buildSharedElementBoxStyle(
  renderPageState(pageState)?.elementLayout?.[id],
  {
    isText: isPageTextElement(pageState, id),
    isLinkedText: isPageLinkedTextElement(pageState, id),
  },
);
const pageElementContentStyle = (pageState, id) => buildSharedElementContentStyle(
  renderPageState(pageState)?.elementLayout?.[id],
  {
    elementType: renderPageState(pageState)?.customElements?.[id]?.type ?? (baseTextElementIds.has(id) ? 'text' : null),
  },
);
const pageRichEditorContainerStyle = (pageState, id) => buildSharedRichEditorContainerStyle(renderPageState(pageState)?.elementLayout?.[id]);
const pageNeonColorOverride = (pageState, id) => neonColorOverrideFromLayout(renderPageState(pageState)?.elementLayout?.[id]);
const pageImageFrameStyle = (pageState, id) => buildImageFrameStyle(renderPageState(pageState)?.elementLayout?.[id]);
const pageImageRenderStyle = (pageState, id) => {
  const renderState = renderPageState(pageState);
  const layout = renderState?.elementLayout?.[id];
  const element = renderState?.customElements?.[id];
  if (!layout || !element) return {};
  return buildCoverImageStyle({
    containerWidth: layout.w ?? 160,
    containerHeight: layout.h ?? 140,
    imageWidth: element.intrinsicWidth,
    imageHeight: element.intrinsicHeight,
    cropScale: layout.imageCropScale,
    cropOffsetX: layout.imageCropOffsetX,
    cropOffsetY: layout.imageCropOffsetY,
    flipX: layout.flipX,
    flipY: layout.flipY,
  });
};
const pageImageTintOverlayStyle = (pageState, id) => buildImageTintOverlayStyle(renderPageState(pageState)?.elementLayout?.[id]);
const pageShapeStyle = (pageState, item) => buildShapeStyle(renderPageState(pageState)?.elementLayout?.[item.id], item.shapeKind, SHAPE_CLIP_PATHS);
const pageShapeRenderModel = (pageState, item) => buildShapeRenderModel(renderPageState(pageState)?.elementLayout?.[item.id], item.shapeKind, SHAPE_CLIP_PATHS);
const pageCanvasBackgroundStyle = (pageState) => buildCanvasBackgroundStyle(renderPageState(pageState)?.elementLayout?.background);
const pageCanvasBackgroundImageSrc = (pageState) => renderPageState(pageState)?.elementLayout?.background?.backgroundImageSrc;
const pageCanvasBackgroundImageStyle = (pageState) => {
  const background = renderPageState(pageState)?.elementLayout?.background ?? {};
  return buildCoverImageStyle({
    containerWidth: editorCanvasDimensions.value.width,
    containerHeight: editorCanvasDimensions.value.height,
    imageWidth: background.backgroundImageWidth,
    imageHeight: background.backgroundImageHeight,
    cropScale: background.backgroundImageCropScale,
    cropOffsetX: background.backgroundImageCropOffsetX,
    cropOffsetY: background.backgroundImageCropOffsetY,
    flipX: background.backgroundImageFlipX,
    flipY: background.backgroundImageFlipY,
    opacity: background.backgroundImageOpacity,
    transparencyLayout: background,
    transparencyPrefix: 'backgroundImage',
    transparencyOpacityKey: 'backgroundImageOpacity',
  });
};
const isTemplateFieldElement = (id) => Boolean(
  isTemplateBaseEditor.value
  && id
  && editorElements.value.find((item) => item.id === id)?.fieldKey
);
const canCloneCurrentSelection = computed(() => {
  if (!isTemplateBaseEditor.value) return true;
  return activeSelectionIds.value.every((id) => !isTemplateFieldElement(id));
});

const designColorOptions = computed(() => {
  const seen = new Set();
  const collected = [];
  const pushColor = (value) => {
    const normalized = normalizeHexCandidate(value);
    if (!normalized || seen.has(normalized)) return;
    seen.add(normalized);
    collected.push(normalized);
  };

  Object.values(state.elementLayout ?? {}).forEach((layout) => {
    if (!layout || typeof layout !== 'object') return;
    [
      layout.backgroundColor,
      layout.color,
      layout.gradientStart,
      layout.gradientEnd,
      layout.contourColor,
      layout.shadowColor,
      layout.neonColor,
      layout.imageTintColor,
      layout.bubbleColor,
    ].forEach(pushColor);

    (layout.paragraphStyles ?? []).forEach((style) => pushColor(style?.color));
  });

  return collected;
});
const designGradientOptions = computed(() => {
  const seen = new Set();
  const collected = [];
  const pushGradient = (start, end) => {
    const normalizedStart = normalizeHexCandidate(start);
    const normalizedEnd = normalizeHexCandidate(end);
    if (!normalizedStart || !normalizedEnd) return;
    const key = `${normalizedStart}-${normalizedEnd}`;
    if (seen.has(key)) return;
    seen.add(key);
    collected.push({ id: `design-${seen.size}`, start: normalizedStart, end: normalizedEnd });
  };

  Object.values(state.elementLayout ?? {}).forEach((layout) => {
    if (layout?.fillMode === 'gradient') {
      pushGradient(layout.gradientStart, layout.gradientEnd);
    }
  });

  return collected;
});
const {
  selectedElement,
  hasSelection,
  isGroupSelection,
  selectedGroup,
  activeSelectionIds,
  hasMultiSelection,
  overlayControlTargetId,
  activeElementLabel,
  selectedElementType,
  hasTextSelection,
  clearSelection,
  clearSelectionMarquee,
  getGroupIdForElement,
  getSelectionBounds,
  isElementSelected,
  startSelectionMarquee,
  updateSelectionMarqueePreview,
  finalizeSelectionMarquee,
  selectGroup,
  buildGroupResizeSnapshot,
  selectedOverlayStyle,
  selectedActionBarStyle,
  selectedHandleMetrics,
  marqueeRectStyle,
} = useEditorSelection({
  state,
  editorElements,
  groupedElements,
  selectedGroupId,
  multiSelectionIds,
  marqueePreviewIds,
  selectionMarquee,
  activePropertyPanel,
  elementMeasurements,
  canvasRef,
  editingElementId,
  commitTextEdit: (...args) => commitTextEdit(...args),
  setDragDocumentState: (...args) => setDragDocumentState(...args),
  getEstimatedTextHeight: (...args) => getEstimatedTextHeight(...args),
  getElementText: (...args) => getElementText(...args),
  ensureParagraphStyles: (...args) => ensureParagraphStyles(...args),
  isTextElement: (...args) => isTextElement(...args),
});
const backgroundHasImage = computed(() => Boolean(state.elementLayout.background?.backgroundImageSrc));
const selectedBackgroundPropertyTabs = computed(() => {
  const tabs = [...backgroundPropertyTabs];

  if (backgroundHasImage.value) {
    tabs.push(
      { id: 'opacity', icon: 'carbon:opacity', title: 'Opacidad', class: 'order-last' },
      { id: 'crop', icon: 'ph:crop-bold', title: 'Recortar', class: 'order-last' },
      { id: 'rotate', icon: '', label: 'Girar', class: 'order-last' },
      { id: 'detach', icon: 'tabler:background', title: 'Separar imagen del fondo', class: 'order-last' },
      { id: 'clear-background', icon: 'ph:trash-bold', title: 'Borrar fondo', class: 'order-last' },
    );
  }

  return tabs;
});
const selectedPropertyTabs = computed(() => {
  if (isGroupSelection.value || hasMultiSelection.value) return [];
  if (!hasSelection.value) return textPropertyTabs;
  if (state.selectedElementId === 'background') return selectedBackgroundPropertyTabs.value;
  if (selectedElementType.value === 'text') return textPropertyTabs;
  return selectedElementType.value === 'image' ? imagePropertyTabs : shapePropertyTabs;
});
const hasSidebarPanelContent = computed(() => (
  !!activePropertyPanel.value
  || textPanelOpen.value
  || imagePanelOpen.value
  || shapePanelOpen.value
));
const isOptionsPanelVisible = computed(() => (
  optionsPanelOpen.value && hasSidebarPanelContent.value
));
const activePropertyTitle = computed(() => {
  const activeTab = selectedPropertyTabs.value.find((tab) => tab.id === activePropertyPanel.value);
  return activeTab?.title ?? activeTab?.label ?? 'Propiedades';
});
const {
  activeTextEffectId,
  activeVisualEffectId,
  textEffectRows,
  visualEffectRows,
  canvasBackgroundStyle,
  normalizePickerColor,
  setSelectedColor,
  setTextEffect,
  setVisualEffect,
  activateBorderStyle,
  textEffectPreviewStyle,
  visualEffectPreviewStyle,
  applyGradientPreset,
  swapGradientStops,
  applyShapeGradientPreset,
  swapShapeGradientStops,
  elementBoxStyle,
  isTextElement,
  isLinkedTextElement,
  isAspectLockedResizeElement,
  shapeStyleFromKind,
  shapeStyle,
  shapeRenderModel,
  imageFrameStyle,
  imageRenderStyle,
  imageTintOverlayStyle,
  elementContentStyle,
  richEditorContainerStyle,
  neonColorOverride,
} = useEditorStyles({
  state,
  selectedElement,
  selectedElementType,
  hasTextSelection,
  textEffectOptions,
  getParagraphStyleFields: () => paragraphStyleFields,
  applyParagraphStyleField: (...args) => applyParagraphStyleField(...args),
  getParagraphStyleForElement: (...args) => getParagraphStyleForElement(...args),
  baseTextElementIds,
  shapeClipPaths: SHAPE_CLIP_PATHS,
});
const orderedLayerIds = computed(() => Object.keys(state.elementLayout).sort((a, b) => {
    const zA = state.elementLayout[a]?.zIndex ?? 0;
    const zB = state.elementLayout[b]?.zIndex ?? 0;

    if (zA === zB) {
        return a.localeCompare(b);
    }

    return zA - zB;
}));
const canvasBackgroundImageStyle = computed(() => buildCoverImageStyle({
  containerWidth: editorCanvasDimensions.value.width,
  containerHeight: editorCanvasDimensions.value.height,
  imageWidth: state.elementLayout.background?.backgroundImageWidth,
  imageHeight: state.elementLayout.background?.backgroundImageHeight,
  cropScale: state.elementLayout.background?.backgroundImageCropScale,
  cropOffsetX: state.elementLayout.background?.backgroundImageCropOffsetX,
  cropOffsetY: state.elementLayout.background?.backgroundImageCropOffsetY,
  flipX: state.elementLayout.background?.backgroundImageFlipX,
  flipY: state.elementLayout.background?.backgroundImageFlipY,
  opacity: state.elementLayout.background?.backgroundImageOpacity,
  transparencyLayout: state.elementLayout.background,
  transparencyPrefix: 'backgroundImage',
  transparencyOpacityKey: 'backgroundImageOpacity',
}));

watch([selectedElementType, hasSelection], () => {
  if (!hasSelection.value) {
    activePropertyPanel.value = null;
    return;
  }

  const availableTabIds = selectedPropertyTabs.value.map((tab) => tab.id);
  if (activePropertyPanel.value && !availableTabIds.includes(activePropertyPanel.value)) {
    activePropertyPanel.value = null;
  }
}, { immediate: true });
watch(hasSidebarPanelContent, (hasContent) => {
  if (!hasContent && optionsPanelOpen.value) {
    optionsPanelOpen.value = false;
  }
});

const paragraphStyleFields = new Set([
    'fontSize',
    'color',
    'fontFamily',
    'fontWeight',
    'italic',
    'underline',
    'uppercase',
    'textAlign',
    'letterSpacing',
    'lineHeight',
]);

const clamp = (value, min, max) => Math.min(Math.max(value, min), max);
const getParagraphs = (text) => String(text ?? '').replace(/\r\n/g, '\n').split('\n');
const buildParagraphStyle = (layout, fallback = {}) => ({
    fontSize: fallback.fontSize ?? layout.fontSize ?? 16,
    color: fallback.color ?? layout.color ?? '#ffffff',
    fontFamily: fallback.fontFamily ?? layout.fontFamily ?? 'Inter, sans-serif',
    fontWeight: fallback.fontWeight ?? layout.fontWeight ?? 'regular',
    italic: fallback.italic ?? layout.italic ?? false,
    underline: fallback.underline ?? layout.underline ?? false,
    uppercase: fallback.uppercase ?? layout.uppercase ?? false,
    textAlign: fallback.textAlign ?? layout.textAlign ?? 'left',
    letterSpacing: fallback.letterSpacing ?? layout.letterSpacing ?? 0,
    lineHeight: fallback.lineHeight ?? layout.lineHeight ?? 1.3,
});
const ensureParagraphStyles = (layout, text = '') => {
    const paragraphs = getParagraphs(text);

    if (!Array.isArray(layout.paragraphStyles)) {
        layout.paragraphStyles = [];
    }

    paragraphs.forEach((_, index) => {
        const current = layout.paragraphStyles[index];
        const previous = layout.paragraphStyles[index - 1];
        const normalized = buildParagraphStyle(layout, current ?? previous ?? {});

        if (!current) {
            layout.paragraphStyles[index] = normalized;
            return;
        }

        Object.entries(normalized).forEach(([key, value]) => {
            if (current[key] === undefined) {
                current[key] = value;
            }
        });
    });

    if (layout.paragraphStyles.length > paragraphs.length) {
        layout.paragraphStyles.splice(paragraphs.length);
    }

    return layout.paragraphStyles;
};

const extractPlainTextFromHtml = (html = '') => {
  if (typeof document === 'undefined') return String(html ?? '');
  const div = document.createElement('div');
  div.innerHTML = html;
  return div.textContent || '';
};

const parseLinkedParagraphStylesFromHtml = (html = '', layout = {}) => {
  if (typeof document === 'undefined') return [];
  const container = document.createElement('div');
  container.innerHTML = html || '';

  const blockNodes = Array.from(container.querySelectorAll('p,div,li,h1,h2,h3,h4,h5,h6,blockquote,pre'));
  if (!blockNodes.length) return [];

  return blockNodes.map((node) => {
    const fallback = buildParagraphStyle(layout);
    const inline = node.style;
    const fontSize = Number.parseFloat(inline.fontSize);
    const letterSpacing = Number.parseFloat(inline.letterSpacing);
    const lineHeight = Number.parseFloat(inline.lineHeight);
    const weightRaw = inline.fontWeight || '';
    const weightNum = Number.parseInt(weightRaw, 10);

    let fontWeight = fallback.fontWeight;
    if (Number.isFinite(weightNum)) {
      fontWeight = weightNum >= 600 ? 'bold' : 'regular';
    } else if (weightRaw) {
      fontWeight = /bold/i.test(weightRaw) ? 'bold' : (/regular|normal/i.test(weightRaw) ? 'regular' : weightRaw);
    }

    return {
      fontSize: Number.isFinite(fontSize) ? fontSize : fallback.fontSize,
      color: inline.color || fallback.color,
      fontFamily: inline.fontFamily || fallback.fontFamily,
      fontWeight,
      italic: inline.fontStyle === 'italic' ? true : fallback.italic,
      underline: /underline/i.test(inline.textDecorationLine || inline.textDecoration || '') ? true : fallback.underline,
      uppercase: inline.textTransform === 'uppercase' ? true : fallback.uppercase,
      textAlign: inline.textAlign || fallback.textAlign,
      letterSpacing: Number.isFinite(letterSpacing) ? letterSpacing : fallback.letterSpacing,
      lineHeight: Number.isFinite(lineHeight) ? lineHeight : fallback.lineHeight,
    };
  });
};

const syncLinkedTextCanonicalFromHtml = (id, html = '') => {
  const headId = getLinkedTextChainHead(id);
  const headElement = linkedTextElementFromAnyPage(headId);
  if (!headElement || headElement.type !== 'linkedText') return;

  const canonicalHtml = String(html ?? '');
  linkedTextSetElementField(headId, 'html', canonicalHtml);
  linkedTextSetElementField(headId, 'text', extractPlainTextFromHtml(canonicalHtml));

  const headLayout = linkedTextLayoutFromAnyPage(headId);
  if (headLayout) {
    const parsedStyles = parseLinkedParagraphStylesFromHtml(canonicalHtml, headLayout);
    linkedTextSetLayoutField(headId, 'paragraphStyles', parsedStyles);
  }

  recalculateLinkedTextAllocations(headId);
};
const getTextSourceForSelectedElement = () => {
    if (!state.selectedElementId) return '';
    return getElementText(state.selectedElementId);
};
const getParagraphStyleForElement = (id, index = 0, text = null) => {
    const styleSourceId = getLinkedTextStyleSourceId(id);
    const layout = state.elementLayout[styleSourceId];
    if (!layout) return null;

    const sourceText = text ?? getElementText(id);
    const styles = ensureParagraphStyles(layout, sourceText);

    return styles[clamp(index, 0, Math.max(0, styles.length - 1))] ?? buildParagraphStyle(layout);
};
const applyParagraphStyleField = (field, value) => {
    if (!selectedElement.value || !state.selectedElementId) return;

    const styleSourceId = getLinkedTextStyleSourceId(state.selectedElementId);
    const layout = state.elementLayout[styleSourceId];
    if (!layout) return;

    const sourceText = getElementText(styleSourceId);
    const styles = ensureParagraphStyles(layout, sourceText);
    const applyToStyle = (style) => {
      style[field] = value;
    };

    if (editingElementId.value === state.selectedElementId && paragraphSelection.active) {
      const start = clamp(Math.min(paragraphSelection.start, paragraphSelection.end), 0, Math.max(0, styles.length - 1));
      const end = clamp(Math.max(paragraphSelection.start, paragraphSelection.end), 0, Math.max(0, styles.length - 1));
      for (let index = start; index <= end; index++) {
        applyToStyle(styles[index]);
      }
    } else if (editingElementId.value === state.selectedElementId) {
      applyToStyle(styles[clamp(selectedParagraphIndex.value, 0, Math.max(0, styles.length - 1))]);
    } else {
      styles.forEach(applyToStyle);
    }

    if (field === 'fontSize' || field === 'fontFamily' || field === 'fontWeight' || field === 'italic' || field === 'letterSpacing' || field === 'lineHeight' || field === 'color') {
      layout[field] = value;
    }

    const editorRef = richEditorRefs.value[state.selectedElementId];

    if (editorRef && editingElementId.value === state.selectedElementId) {
        editorRef.applyStyle(field, value);
    } else if (editorRef) {
        editorRef.applyStyleAll(field, value);
    }

    if (state.customElements?.[styleSourceId]?.type === 'linkedText') {
      recalculateLinkedTextAllocations(getLinkedTextChainHead(styleSourceId));
    }
};
const selectedTextStyle = computed(() => {
    if (!state.selectedElementId) return {};

  const fallbackStyle = selectedElement.value
    ? (getParagraphStyleForElement(
      state.selectedElementId,
      selectedParagraphIndex.value,
      getTextSourceForSelectedElement(),
    ) ?? buildParagraphStyle(selectedElement.value))
    : {};

    const editorRef = richEditorRefs.value[state.selectedElementId];
  const activeAttrs = editorRef?.getActiveAttrs() ?? {};
  const mergedAttrs = Object.fromEntries(
    Object.entries(activeAttrs).filter(([, value]) => value !== null && value !== undefined)
  );
  const attrs = buildParagraphStyle(selectedElement.value ?? {}, {
    ...fallbackStyle,
    ...mergedAttrs,
  });

  return new Proxy(attrs, {
        get(target, key) {
            return target[key];
        },
        set(_, key, value) {
            if (typeof key !== 'string') return true;
            if (paragraphStyleFields.has(key)) {
                applyParagraphStyleField(key, value);
            }
            return true;
        },
    });
});
const paragraphCount = computed(() => {
    if (!selectedElement.value || !state.selectedElementId) return 0;
    return selectedElement.value.paragraphStyles?.length
        || getParagraphs(getElementText(state.selectedElementId)).length;
});
const activeParagraphLabel = computed(() => {
    if (!paragraphCount.value) return 'Párrafo 1 de 1';

    if (editingElementId.value !== state.selectedElementId) {
        return paragraphCount.value === 1 ? 'Todo el texto (1 párrafo)' : `Todo el texto (${paragraphCount.value} párrafos)`;
    }

    const n = paragraphCount.value;
    const first = paragraphSelection.start + 1;
    const last = paragraphSelection.end + 1;

    if (!paragraphSelection.active || first === last) {
        return `Párrafo ${selectedParagraphIndex.value + 1} de ${n}`;
    }

    return `Párrafos ${Math.min(first, last)}-${Math.max(first, last)} de ${n}`;
});

const getMaxZIndex = () => Object.values(state.elementLayout).reduce((max, layout) => Math.max(max, layout?.zIndex ?? 0), 0);
const resolvedSizeOption = computed(() => {
  const options = resolveObjectiveSizeOptions(state.objective, state.outputType, state.format);
  return options.find((option) => option.label === state.size) ?? null;
});
const selectedSizeDetail = computed(() => resolvedSizeOption.value?.detail ?? state.size ?? '1080 ? 1080 px');
const editorCanvasDimensions = computed(() => {
  const parsed = applyFormatToDimensions(parseSizeDetail(selectedSizeDetail.value), state.format);
  if (parsed?.width > 0 && parsed?.height > 0) {
    const ratio = parsed.width / parsed.height;
    if (ratio >= 0.95 && ratio <= 1.05) {
      return {
        width: 500,
        height: 500,
      };
    }

    if (ratio > 1) {
      return {
        width: BASE_CANVAS_LONG_SIDE,
        height: Math.max(300, Math.min(BASE_CANVAS_LONG_SIDE, Math.round(BASE_CANVAS_LONG_SIDE / ratio))),
      };
    }

    return {
      width: Math.max(300, Math.min(BASE_CANVAS_LONG_SIDE, Math.round(BASE_CANVAS_LONG_SIDE * ratio))),
      height: BASE_CANVAS_LONG_SIDE,
    };
  }

  if (isHorizontalFormat(state.format)) {
    return { width: BASE_CANVAS_LONG_SIDE, height: BASE_CANVAS_SHORT_SIDE };
  }

  if (state.format === 'square') {
    return { width: 500, height: 500 };
  }

  return { width: BASE_CANVAS_SHORT_SIDE, height: BASE_CANVAS_LONG_SIDE };
});
const canvasGridStyle = computed(() => ({
  minHeight: `${editorCanvasDimensions.value.height + 96}px`,
}));
const editorGridStyle = computed(() => {
  if (isMobileEditor.value) {
    return { gridTemplateColumns: 'minmax(0,1fr)' };
  }

  return {
    gridTemplateColumns: `${isOptionsPanelVisible.value ? '70px 320px' : '70px'} minmax(0,1fr)${isTemplateBaseEditor.value ? ' 320px' : ''}`,
  };
});
const canvasFrameStyle = computed(() => ({
  width: `${editorCanvasDimensions.value.width}px`,
  maxWidth: '100%',
}));
const canvasFrameContainerStyle = computed(() => ({
  ...canvasFrameStyle.value,
  height: `${editorCanvasDimensions.value.height}px`,
}));
const canvasZoomStyle = computed(() => ({
  transform: `scale(${zoomLevel.value / 100})`,
  transformOrigin: 'top center',
}));
const zoomScale = computed(() => Math.max(0.25, zoomLevel.value / 100));
const pageViewportStyle = computed(() => ({
  height: `${Math.ceil((editorCanvasDimensions.value.height + (isBrochureDocument() ? 74 : 42)) * zoomScale.value)}px`,
}));
const pageChromeStyle = computed(() => ({
  ...canvasFrameStyle.value,
  transform: `translateX(-50%) scale(${zoomScale.value})`,
  transformOrigin: 'top center',
}));
const addPageButtonViewportStyle = computed(() => ({
  height: `${Math.ceil(48 * zoomScale.value)}px`,
}));
const controlZoomStyle = computed(() => ({
  transform: `scale(${Math.max(0.1, Math.min(4, 100 / zoomLevel.value))})`,
  transformOrigin: 'center center',
}));
const canvasElementStyle = computed(() => ({
  width: `${editorCanvasDimensions.value.width}px`,
  height: `${editorCanvasDimensions.value.height}px`,
}));
const setZoomLevel = (value) => {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return;
  zoomLevel.value = Math.round(clamp(parsed, 25, 200));
};

const handleCanvasWheel = (event) => {
  if (!event.ctrlKey) return;

  if (event.cancelable) {
    event.preventDefault();
  }
  event.stopPropagation();

  const scrollElement = event.currentTarget;
  const previousZoom = zoomLevel.value;
  const direction = event.deltaY < 0 ? 1 : -1;
  const nextZoom = Math.round(clamp(previousZoom + (direction * 10), 25, 200));

  if (!scrollElement || nextZoom === previousZoom) {
    return;
  }

  const scrollRect = scrollElement.getBoundingClientRect();
  const focusX = scrollElement.scrollLeft + event.clientX - scrollRect.left;
  const focusY = scrollElement.scrollTop + event.clientY - scrollRect.top;
  const ratio = nextZoom / Math.max(1, previousZoom);

  setZoomLevel(nextZoom);

  nextTick(() => {
    scrollElement.scrollLeft = Math.max(0, (focusX * ratio) - (event.clientX - scrollRect.left));
    scrollElement.scrollTop = Math.max(0, (focusY * ratio) - (event.clientY - scrollRect.top));
  });
};

const getCanvasScrollContainer = () => canvasRef.value?.closest?.('.canvas-grid') ?? null;
const getPinchTouchPoints = () => [...pinchPointers.values()].slice(0, 2);
const getPinchDistance = ([first, second]) => Math.hypot(second.clientX - first.clientX, second.clientY - first.clientY);
const getPinchCenter = ([first, second]) => ({
  clientX: (first.clientX + second.clientX) / 2,
  clientY: (first.clientY + second.clientY) / 2,
});

const resetActivePointerGesturesForPinch = () => {
  selectionMarquee.active = false;
  selectionMarquee.pointerId = null;
  marqueePreviewIds.value = [];
  drag.active = false;
  drag.pointerId = null;
  drag.elementId = null;
  drag.groupId = null;
  dragIntent.active = false;
  dragIntent.pointerId = null;
  touchIntent.pointerId = null;
  toolbarDrag.active = false;
  toolbarDrag.pointerId = null;
};

const beginPinchZoom = (event) => {
  const scrollElement = getCanvasScrollContainer();
  const points = getPinchTouchPoints();
  if (!scrollElement || points.length < 2) return false;

  const distance = getPinchDistance(points);
  if (distance < 12) return false;

  const center = getPinchCenter(points);
  const scrollRect = scrollElement.getBoundingClientRect();

  resetActivePointerGesturesForPinch();
  pinchZoom.active = true;
  pinchZoom.startDistance = distance;
  pinchZoom.startZoom = zoomLevel.value;
  pinchZoom.focusX = scrollElement.scrollLeft + center.clientX - scrollRect.left;
  pinchZoom.focusY = scrollElement.scrollTop + center.clientY - scrollRect.top;
  setDragDocumentState(true);

  if (event?.cancelable) event.preventDefault();
  return true;
};

const applyPinchZoom = (nextZoom, center) => {
  const scrollElement = getCanvasScrollContainer();
  if (!scrollElement) return;

  const scrollRect = scrollElement.getBoundingClientRect();
  const centerX = center.clientX - scrollRect.left;
  const centerY = center.clientY - scrollRect.top;
  const ratio = nextZoom / Math.max(1, pinchZoom.startZoom);

  setZoomLevel(nextZoom);

  nextTick(() => {
    scrollElement.scrollLeft = Math.max(0, pinchZoom.focusX * ratio - centerX);
    scrollElement.scrollTop = Math.max(0, pinchZoom.focusY * ratio - centerY);
  });
};

const handleCanvasPointerDownWithPinch = (event) => {
  if (event.pointerType === 'touch') {
    pinchPointers.set(event.pointerId, {
      pointerId: event.pointerId,
      clientX: event.clientX,
      clientY: event.clientY,
    });

    if (pinchPointers.size >= 2 && beginPinchZoom(event)) {
      return;
    }
  }

  handleCanvasPointerDown(event);
};

const handlePinchPointerMove = (event) => {
  if (!pinchPointers.has(event.pointerId)) return;

  pinchPointers.set(event.pointerId, {
    pointerId: event.pointerId,
    clientX: event.clientX,
    clientY: event.clientY,
  });

  if (!pinchZoom.active && pinchPointers.size >= 2) {
    beginPinchZoom(event);
  }

  if (!pinchZoom.active) return;

  const points = getPinchTouchPoints();
  if (points.length < 2 || pinchZoom.startDistance <= 0) return;

  const distance = getPinchDistance(points);
  const center = getPinchCenter(points);
  const nextZoom = clamp(pinchZoom.startZoom * (distance / pinchZoom.startDistance), 25, 200);

  applyPinchZoom(nextZoom, center);
  if (event.cancelable) event.preventDefault();
};

const handlePinchPointerEnd = (event) => {
  if (!pinchPointers.has(event.pointerId)) return;

  pinchPointers.delete(event.pointerId);

  if (!pinchZoom.active || pinchPointers.size >= 2) return;

  pinchZoom.active = false;
  pinchZoom.startDistance = 0;
  pinchZoom.startZoom = zoomLevel.value;
  setDragDocumentState(false);
};
const currentCanvasDimensions = () => ({
  width: editorCanvasDimensions.value.width,
  height: editorCanvasDimensions.value.height,
});
const canvasDimensionsForDesignerState = (snapshot = {}) => {
  const options = resolveObjectiveSizeOptions(snapshot.objective, snapshot.outputType, snapshot.format);
  const option = options.find((item) => item.label === snapshot.size) ?? null;
  const parsed = applyFormatToDimensions(parseSizeDetail(option?.detail ?? snapshot.size ?? '1080 Ã— 1080 px'), snapshot.format);

  if (parsed?.width > 0 && parsed?.height > 0) {
    const ratio = parsed.width / parsed.height;
    if (ratio >= 0.95 && ratio <= 1.05) {
      return { width: 500, height: 500 };
    }

    if (ratio > 1) {
      return {
        width: BASE_CANVAS_LONG_SIDE,
        height: Math.max(300, Math.min(BASE_CANVAS_LONG_SIDE, Math.round(BASE_CANVAS_LONG_SIDE / ratio))),
      };
    }

    return {
      width: Math.max(300, Math.min(BASE_CANVAS_LONG_SIDE, Math.round(BASE_CANVAS_LONG_SIDE * ratio))),
      height: BASE_CANVAS_LONG_SIDE,
    };
  }

  if (isHorizontalFormat(snapshot.format)) {
    return { width: BASE_CANVAS_LONG_SIDE, height: BASE_CANVAS_SHORT_SIDE };
  }

  if (snapshot.format === 'square') {
    return { width: 500, height: 500 };
  }

  return { width: BASE_CANVAS_SHORT_SIDE, height: BASE_CANVAS_LONG_SIDE };
};
const getCanvasBounds = () => ({
  width: canvasRef.value?.clientWidth ?? editorCanvasDimensions.value.width,
  height: canvasRef.value?.clientHeight ?? editorCanvasDimensions.value.height,
});
const getInsertX = (elementWidth = 280) => {
  const bounds = getCanvasBounds();
  const width = Math.max(40, elementWidth);
  const maxX = Math.max(0, bounds.width - width - 8);
  const centeredX = Math.round((bounds.width - width) / 2);
  return Math.round(clamp(centeredX, 0, maxX));
};
const createElementId = (prefix) => {
  const suffix = Math.random().toString(36).slice(2, 9);
  return `${prefix}-${Date.now().toString(36)}-${suffix}`;
};
const buildDefaultLayout = (overrides = {}) => ({
  x: 24,
  y: 40,
  w: 280,
  rotation: 0,
  zIndex: getMaxZIndex() + 10,
  fontSize: 18,
  color: '#ffffff',
  shadow: false,
  border: false,
  borderStyle: 'solid',
  fontFamily: 'Inter, sans-serif',
  opacity: 100,
  fontWeight: 'regular',
  italic: false,
  underline: false,
  uppercase: false,
  textAlign: 'left',
  letterSpacing: 0,
  lineHeight: 1.4,
  shadowPreset: 'soft',
  shadowColor: '#0f172a',
  contourWidth: 2,
  contourColor: '#ffffff',
  hollowText: false,
  neonColor: '',
  shadowAngle: 135,
  shadowOffset: 22,
  shadowBlur: 28,
  shadowOpacity: 65,
  misalignedThickness: 6,
  neonIntensity: 55,
  bubbleColor: 'transparent',
  backgroundColor: 'transparent',
  backgroundRoundness: 50,
  backgroundPadding: 5,
  backgroundOpacity: 70,
  textEffectMode: 'none',
  fillMode: 'solid',
  gradientStart: '#0ea5e9',
  gradientEnd: '#8b5cf6',
  gradientAngle: 135,
  imageTintColor: '#0f172a',
  imageTintStrength: 0,
  imageCropScale: 1,
  imageCropOffsetX: 0,
  imageCropOffsetY: 0,
  flipX: false,
  flipY: false,
  borderRadius: 12,
  borderRadiusTopLeft: null,
  borderRadiusTopRight: null,
  borderRadiusBottomRight: null,
  borderRadiusBottomLeft: null,
  transparencyType: 'flat',
  transparencyFadeOpacity: 0,
  transparencyCenterX: 50,
  transparencyCenterY: 50,
  transparencyRadius: 70,
  transparencyRadiusX: 70,
  transparencyRadiusY: 45,
  transparencyRotation: 0,
  transparencyStartX: 0,
  transparencyStartY: 50,
  transparencyEndX: 100,
  transparencyEndY: 50,
  transparencyEasing: 'linear',
  ...overrides,
});
const placeInsideCanvas = (layout) => {
  const bounds = getCanvasBounds();
  const width = Math.max(40, layout.w ?? 0);
  const height = Math.max(40, layout.h ?? 50);

  layout.x = Math.round(clamp(layout.x ?? 0, 0, Math.max(0, bounds.width - width - 8)));
  layout.y = Math.round(clamp(layout.y ?? 0, 18, Math.max(18, bounds.height - height - 8)));
};

const normalizeColorKey = (value) => {
  if (typeof value !== 'string') return null;
  const trimmed = value.trim().toLowerCase();
  if (!trimmed || trimmed === 'transparent') return null;
  return trimmed;
};
const getDominantTextColor = () => {
  const counts = new Map();
  const firstSeen = new Map();
  let order = 0;

  editorElements.value.forEach((item) => {
    if (item.type !== 'text') return;
    const layout = state.elementLayout?.[item.id];
    if (!layout) return;

    const colors = [
      layout.color,
      ...(Array.isArray(layout.paragraphStyles)
        ? layout.paragraphStyles.map((style) => style?.color)
        : []),
    ];

    colors.forEach((color) => {
      const key = normalizeColorKey(color);
      if (!key) return;
      counts.set(key, (counts.get(key) ?? 0) + 1);
      if (!firstSeen.has(key)) {
        firstSeen.set(key, order);
        order += 1;
      }
    });
  });

  if (!counts.size) return '#1f2937';

  return Array.from(counts.entries())
    .sort((a, b) => (b[1] - a[1]) || ((firstSeen.get(a[0]) ?? 0) - (firstSeen.get(b[0]) ?? 0)))[0][0];
};

const scaleNumericField = (layout, field, factor, minimum = 0) => {
  if (!Number.isFinite(Number(layout?.[field]))) return;
  layout[field] = Math.max(minimum, Number(layout[field]) * factor);
};

const rescaleDesignSurface = (previousSurface, nextSurface) => {
  if (!previousSurface?.width || !previousSurface?.height || !nextSurface?.width || !nextSurface?.height) {
    state.designSurface = nextSurface;
    return;
  }

  const widthScale = nextSurface.width / previousSurface.width;
  const heightScale = nextSurface.height / previousSurface.height;
  const averageScale = (widthScale + heightScale) / 2;

  Object.entries(state.elementLayout ?? {}).forEach(([id, layout]) => {
    if (!layout || id === 'background') return;

    scaleNumericField(layout, 'x', widthScale);
    scaleNumericField(layout, 'y', heightScale, 18);
    scaleNumericField(layout, 'w', widthScale, 40);
    scaleNumericField(layout, 'h', heightScale, 40);
    scaleNumericField(layout, 'fontSize', averageScale, 8);
    scaleNumericField(layout, 'shadowOffset', averageScale);
    scaleNumericField(layout, 'shadowBlur', averageScale);
    scaleNumericField(layout, 'contourWidth', averageScale);
    scaleNumericField(layout, 'misalignedThickness', averageScale);
    scaleNumericField(layout, 'backgroundPadding', averageScale);
    scaleNumericField(layout, 'letterSpacing', averageScale);

    if (Array.isArray(layout.paragraphStyles)) {
      layout.paragraphStyles = layout.paragraphStyles.map((style) => ({
        ...style,
        fontSize: Number.isFinite(Number(style?.fontSize)) ? Math.max(8, Number(style.fontSize) * averageScale) : style?.fontSize,
        letterSpacing: Number.isFinite(Number(style?.letterSpacing)) ? Number(style.letterSpacing) * averageScale : style?.letterSpacing,
      }));
    }

    // Do not clamp persisted layouts during editor hydration/rescaling.
    // Users may intentionally place text flush with, or partially beyond, an edge.
  });

  state.designSurface = nextSurface;
};

const addTextElement = (presetId) => {
  activateVisibleDocumentPage();
  const preset = textPresets.find((item) => item.id === presetId);
  if (!preset) return;

  const id = createElementId('text');
  const layout = buildDefaultLayout({
    w: preset.width,
    fontSize: preset.fontSize,
    fontWeight: preset.fontWeight,
    lineHeight: preset.lineHeight,
    color: '#ffffff',
    shadow: presetId === 'heading',
    x: getInsertX(preset.width),
    y: 90,
    paragraphStyles: [{
      fontSize: preset.fontSize,
      color: '#ffffff',
      fontFamily: 'Poppins, sans-serif',
      fontWeight: preset.fontWeight,
      italic: false,
      underline: false,
      uppercase: false,
      textAlign: 'left',
      letterSpacing: 0,
      lineHeight: preset.lineHeight,
    }],
  });

  placeInsideCanvas(layout);
  state.customElements = {
    ...(state.customElements ?? {}),
    [id]: {
    id,
    type: 'text',
    label: preset.label,
    text: preset.preview,
    },
  };
  state.elementLayout = {
    ...(state.elementLayout ?? {}),
    [id]: layout,
  };
  state.selectedElementId = id;
};

const addLinkedTextElement = () => {
  activateVisibleDocumentPage();
  const groupId = `linked-group-${Date.now()}`;
  const id = `linked-text-${Date.now()}`;
  const layout = buildDefaultLayout({
    w: 300,
    h: 120,
    fontSize: 18,
    fontWeight: 'regular',
    lineHeight: 1.4,
    color: '#ffffff',
    shadow: false,
    x: getInsertX(300),
    y: 90,
    linkedTextGroupId: groupId,
    linkedTextNext: null,
    linkedTextPrev: null,
    linkedTextChainIndex: 0,
    paragraphStyles: [{
      fontSize: 18,
      color: '#ffffff',
      fontFamily: 'Poppins, sans-serif',
      fontWeight: 'regular',
      italic: false,
      underline: false,
      uppercase: false,
      textAlign: 'left',
      letterSpacing: 0,
      lineHeight: 1.4,
    }],
  });

  placeInsideCanvas(layout);
  state.customElements = {
    ...(state.customElements ?? {}),
    [id]: {
      id,
      type: 'linkedText',
      label: 'Texto enlazado',
      text: 'Escribe tu texto aquí...',
    },
  };
  state.elementLayout = {
    ...(state.elementLayout ?? {}),
    [id]: layout,
  };
  state.selectedElementId = id;
};

const handleLinkedTextLinkStart = ({ event, id }) => {
  linkedTextLink.active = true;
  linkedTextLink.sourceId = id;
  linkedTextLink.currentX = event.clientX;
  linkedTextLink.currentY = event.clientY;
  if (canvasRef.value) {
    const rect = canvasRef.value.getBoundingClientRect();
    linkedTextLink.canvasX = event.clientX - rect.left;
    linkedTextLink.canvasY = event.clientY - rect.top;
  }
  event.target.setPointerCapture(event.pointerId);
};

const handleLinkedTextLinkMove = (event) => {
  if (!linkedTextLink.active) return;
  linkedTextLink.currentX = event.clientX;
  linkedTextLink.currentY = event.clientY;
  if (canvasRef.value) {
    const rect = canvasRef.value.getBoundingClientRect();
    linkedTextLink.canvasX = event.clientX - rect.left;
    linkedTextLink.canvasY = event.clientY - rect.top;
  }
  const targetElement = document.elementFromPoint(event.clientX, event.clientY);
  const targetEditorElement = targetElement?.closest('[data-editor-element="true"]');
  const targetId = targetEditorElement?.dataset.editorId;
  if (targetId && linkedTextElementFromAnyPage(targetId)?.type === 'linkedText' && targetId !== linkedTextLink.sourceId) {
    linkedTextLink.hoverTargetId = targetId;
  } else {
    linkedTextLink.hoverTargetId = null;
    linkedTextLink._lastHoverId = null;
  }
};

const handleLinkedTextLinkEnd = ({ event, targetId }) => {
  if (!linkedTextLink.active || !linkedTextLink.sourceId) return;

  if (targetId && targetId !== linkedTextLink.sourceId) {
    const sourceLayout = linkedTextLayoutFromAnyPage(linkedTextLink.sourceId);
    const targetLayout = linkedTextLayoutFromAnyPage(targetId);
    if (sourceLayout && targetLayout) {
      const oldNextId = sourceLayout.linkedTextNext;
      if (oldNextId && oldNextId !== targetId) {
        const oldNextLayout = linkedTextLayoutFromAnyPage(oldNextId);
        if (oldNextLayout) {
          linkedTextSetLayoutField(oldNextId, 'linkedTextPrev', null);
        }
      }

      const oldPrevId = targetLayout.linkedTextPrev;
      if (oldPrevId && oldPrevId !== linkedTextLink.sourceId) {
        const oldPrevLayout = linkedTextLayoutFromAnyPage(oldPrevId);
        if (oldPrevLayout?.linkedTextNext === targetId) {
          linkedTextSetLayoutField(oldPrevId, 'linkedTextNext', null);
          recalculateLinkedTextAllocations(getLinkedTextChainHead(oldPrevId));
        }
      }

      const sourceGroupId = sourceLayout.linkedTextGroupId;
      const targetGroupId = targetLayout.linkedTextGroupId;
      const newGroupId = sourceGroupId || targetGroupId || `linked-group-${Date.now()}`;

      linkedTextSetLayoutField(linkedTextLink.sourceId, 'linkedTextGroupId', newGroupId);
      linkedTextSetLayoutField(linkedTextLink.sourceId, 'linkedTextNext', targetId);
      linkedTextSetLayoutField(targetId, 'linkedTextGroupId', newGroupId);
      linkedTextSetLayoutField(targetId, 'linkedTextPrev', linkedTextLink.sourceId);

      const chain = getLinkedTextChain(linkedTextLink.sourceId);
      chain.forEach((item, index) => {
        linkedTextSetLayoutField(item.id, 'linkedTextChainIndex', index);
        linkedTextSetLayoutField(item.id, 'linkedTextGroupId', newGroupId);
      });

      recalculateLinkedTextAllocations(linkedTextLink.sourceId);
    }
  }

  linkedTextLink.active = false;
  linkedTextLink.sourceId = null;
  linkedTextLink.hoverTargetId = null;
};

const handleLinkedTextLinkBreak = (event) => {
  const sourceId = linkedTextLink.sourceId;
  if (!sourceId) return;
  const sourceLayout = linkedTextLayoutFromAnyPage(sourceId);
  if (!sourceLayout?.linkedTextNext) return;

  const nextId = sourceLayout.linkedTextNext;
  const nextLayout = linkedTextLayoutFromAnyPage(nextId);
  if (!nextLayout) return;

  const groupId = sourceLayout.linkedTextGroupId;
  const fragment = linkedTextBoxSystem.getFragmentForBox(groupId, nextId);
  const nextHtml = fragment.tailHtml || fragment.html || '';

  linkedTextSetLayoutField(sourceId, 'linkedTextNext', null);
  linkedTextSetLayoutField(nextId, 'linkedTextPrev', null);

  const newGroupId = `linked-group-${Date.now()}`;
  let currentWalkId = nextId;
  const visited = new Set();
  while (currentWalkId && !visited.has(currentWalkId)) {
    visited.add(currentWalkId);
    const walkLayout = linkedTextLayoutFromAnyPage(currentWalkId);
    if (!walkLayout) break;
    linkedTextSetLayoutField(currentWalkId, 'linkedTextGroupId', newGroupId);
    currentWalkId = walkLayout.linkedTextNext;
  }

  const nextElement = linkedTextElementFromAnyPage(nextId);
  if (nextElement?.type === 'linkedText') {
    linkedTextSetElementField(nextId, 'html', nextHtml);
    linkedTextSetElementField(nextId, 'text', nextHtml.replace(/<[^>]*>/g, ''));
  }

  recalculateLinkedTextAllocations(sourceId);
  recalculateLinkedTextAllocations(nextId);

  frontendLog.info('linkBreak', `Enlace roto entre ${sourceId} y ${nextId}`);
};

const redistributeLinkedText = (startId) => {
  const headId = getLinkedTextChainHead(startId);
  const sourceElement = state.customElements[headId];
  if (!sourceElement || sourceElement.type !== 'linkedText') return;
  const fullText = sourceElement.text || '';
  const chain = getLinkedTextChain(headId);
  if (chain.length < 2) return;
  const chainLayouts = chain.map((item) => {
    const l = state.elementLayout[item.id];
    return {
      w: l?.w || 300,
      h: l?.h || 120,
      fontSize: l?.fontSize || 18,
      fontFamily: l?.fontFamily || 'Poppins, sans-serif',
      fontWeight: l?.fontWeight || 'regular',
      italic: l?.italic || false,
      letterSpacing: l?.letterSpacing || 0,
      lineHeight: l?.lineHeight || 1.4,
      paragraphStyles: l?.paragraphStyles || [],
    };
  });
  const distributed = distributeTextInLinkedChain(fullText, chainLayouts);
  chain.forEach((item, index) => {
    const element = state.customElements[item.id];
    if (element && element.type === 'linkedText') {
      element.text = distributed[index] || '';
    }
  });
};

const onRichEditorHtmlUpdate = (id, html) => {
  const element = linkedTextElementFromAnyPage(id);
  if (!element || element.type !== 'linkedText') return;

  const layout = linkedTextLayoutFromAnyPage(id);
  if (!layout?.linkedTextGroupId) {
    syncLinkedTextCanonicalFromHtml(id, html);
    return;
  }

  const fragment = linkedTextBoxSystem.getFragmentForBox(layout.linkedTextGroupId, id);
  syncLinkedTextCanonicalFromHtml(id, `${fragment.prefixHtml || ''}${html || ''}`);
};

const addTemplateFieldElement = (fieldKey) => {
  if (!fieldKey || state.elementLayout?.[fieldKey]) return;

  const preset = fieldKey === 'title'
    ? textPresets[0]
    : fieldKey === 'subtitle'
      ? textPresets[1]
      : textPresets[2];

  const fallbackFieldLabel = templateFieldDefinitions.value.find((field) => field.id === fieldKey)?.label
    ?? templateFieldLabels[fieldKey]
    ?? fieldKey;
  const currentContentValue = String(state.content?.[fieldKey] ?? '');
  const fallbackFieldText = templateFieldDefaultTexts[fieldKey] ?? `${fallbackFieldLabel} de prueba`;
  const defaultText = fieldKey === 'meta'
    ? (hasMeaningfulText(metaLine.value) ? metaLine.value : templateFieldDefaultTexts.meta)
    : (hasMeaningfulText(currentContentValue) ? currentContentValue : fallbackFieldText);

  if (fieldKey === 'meta' && !hasMeaningfulText(metaLine.value)) {
    state.content.date = hasMeaningfulText(state.content.date) ? state.content.date : templateFieldDefaultTexts.date;
    state.content.time = hasMeaningfulText(state.content.time) ? state.content.time : templateFieldDefaultTexts.time;
  } else if (templateContentFieldIds.has(fieldKey) && !hasMeaningfulText(state.content?.[fieldKey])) {
    state.content[fieldKey] = fallbackFieldText;
  }

  const id = fieldKey;
  const width = fieldKey === 'extra' ? 360 : (fieldKey === 'meta' ? 280 : preset.width);
  const defaultTextColor = getDominantTextColor();
  const layout = buildDefaultLayout({
    w: width,
    fontSize: preset.fontSize,
    fontWeight: preset.fontWeight,
    lineHeight: preset.lineHeight,
    color: defaultTextColor,
    shadow: fieldKey === 'title',
    x: getInsertX(width),
    y: 90,
    paragraphStyles: [{
      fontSize: preset.fontSize,
      color: defaultTextColor,
      fontFamily: 'Poppins, sans-serif',
      fontWeight: preset.fontWeight,
      italic: false,
      underline: false,
      uppercase: false,
      textAlign: 'left',
      letterSpacing: 0,
      lineHeight: preset.lineHeight,
    }],
  });

  placeInsideCanvas(layout);
  state.customElements = {
    ...(state.customElements ?? {}),
    [id]: {
      id,
      type: 'text',
      label: templateFieldLabels[fieldKey] ?? fieldKey,
      fieldKey,
      text: defaultText,
    },
  };
  state.elementLayout = {
    ...(state.elementLayout ?? {}),
    [id]: layout,
  };
  state.selectedElementId = id;
};

const removeTemplateFieldElement = (fieldKey) => {
  if (!fieldKey || !state.elementLayout?.[fieldKey]) return;
  clearContentForRemovedTextElement(fieldKey);
  delete state.elementLayout[fieldKey];
  if (state.customElements?.[fieldKey]) {
    const next = { ...(state.customElements ?? {}) };
    delete next[fieldKey];
    state.customElements = next;
  }
  if (state.selectedElementId === fieldKey) {
    state.selectedElementId = null;
    activePropertyPanel.value = null;
  }
};

const clearContentForRemovedTextElement = (id) => {
  if (!id) return;

  if (templateContentFieldIds.has(id)) {
    state.content[id] = '';
    return;
  }

  if (id === 'meta') {
    state.content.date = '';
    state.content.time = '';
  }
};

const closeImagePanel = () => {
  imagePanelOpen.value = false;
  imageUrlInput.value = '';
};

const requestImmediateStateFlush = () => {
  flushDesignerStatePersistence().catch((error) => {
    console.error('No se pudo persistir inmediatamente el estado del editor', error);
  });
};

const resolveThumbnailBackgroundColor = (pageState = null) => {
  const background = (pageState?.elementLayout ?? state.elementLayout)?.background;

  if (background?.fillMode === 'gradient') {
    return null;
  }

  if (background?.backgroundColor && background.backgroundColor !== 'transparent') {
    return background.backgroundColor;
  }

  return '#ffffff';
};



// Genera la miniatura y ejecuta un callback cuando estÃ© lista
const generateThumbnailAndThen = (cb) => {
  if (thumbnailTimer) {
    clearTimeout(thumbnailTimer);
  }
  thumbnailTimer = setTimeout(async () => {
    thumbnailTimer = null;
    await nextTick();
    setTimeout(async () => {
      try {
        const firstPageId = state.pages?.[0]?.id;
        const firstPageCanvas = firstPageId
          ? documentPageRefs.get(firstPageId)?.querySelector?.('[data-editor-canvas="true"]')
          : null;
        const thumbnailCanvas = firstPageCanvas ?? canvasRef.value;
        if (thumbnailCanvas) {
          const { toJpegExport } = await import('../../utils/useHtml2Image');
          const dataUrl = await toJpegExport(thumbnailCanvas, {
            quality: 0.6,
            pixelRatio: 0.35,
            backgroundColor: resolveThumbnailBackgroundColor(state.pages?.[0] ?? null),
            filter: (node) => !(node instanceof Element && node.closest?.('[data-editor-control="true"]')),
          });
          const hash = await crypto.subtle.digest('SHA-1', new TextEncoder().encode(dataUrl));
          const hashArray = Array.from(new Uint8Array(hash));
          const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
          setDesignerThumbnailDataUrl(dataUrl, hashHex);
        }
      } catch (error) {
        // Error generando thumbnail; el estado debe guardarse igualmente.
      } finally {
        if (typeof cb === 'function') {
          await cb();
        }
      }
    }, 0);
  }, 1200);
};

const getUploadedImageIndexByAssetId = (assetId) => state.userUploadedImages.findIndex(
  (image) => String(image?.assetId ?? '') === String(assetId ?? '') || String(image?.id ?? '') === String(assetId ?? '')
);

const getUploadedImageByAssetId = (assetId) => {
  const index = getUploadedImageIndexByAssetId(assetId);
  return index >= 0 ? state.userUploadedImages[index] : null;
};

const upsertUploadedImage = (entry) => {
  if (!entry?.assetId) return null;

  const normalizedEntry = {
    id: entry.id ?? entry.assetId,
    assetId: entry.assetId,
    label: entry.label ?? 'Subida',
    src: entry.src ?? '',
    pendingDataUrl: entry.pendingDataUrl ?? null,
    storagePath: entry.storagePath ?? null,
    uploadStatus: entry.uploadStatus ?? 'done',
    needsUpload: Boolean(entry.needsUpload),
    errorMessage: entry.errorMessage ?? null,
    intrinsicWidth: Number(entry.intrinsicWidth ?? 0) || null,
    intrinsicHeight: Number(entry.intrinsicHeight ?? 0) || null,
  };

  const existingIndex = getUploadedImageIndexByAssetId(entry.assetId);
  const duplicateSourceIndex = existingIndex >= 0 ? existingIndex : state.userUploadedImages.findIndex((image) => (
    (normalizedEntry.storagePath && image?.storagePath === normalizedEntry.storagePath)
    || (normalizedEntry.src && image?.src === normalizedEntry.src)
  ));
  if (duplicateSourceIndex >= 0) {
    state.userUploadedImages.splice(duplicateSourceIndex, 1, {
      ...state.userUploadedImages[duplicateSourceIndex],
      ...normalizedEntry,
    });
    return state.userUploadedImages[duplicateSourceIndex];
  }

  state.userUploadedImages.unshift(normalizedEntry);
  return state.userUploadedImages[0];
};

const updateUploadedImage = (assetId, updater) => {
  const existing = getUploadedImageByAssetId(assetId);
  if (!existing) return null;

  const nextValue = typeof updater === 'function' ? updater(existing) : updater;
  if (!nextValue) return existing;

  return upsertUploadedImage({
    ...existing,
    ...nextValue,
    assetId,
  });
};

const getUploadProgress = (assetId) => {
  const progress = uploadProgressByAssetId[assetId];
  if (typeof progress === 'number') {
    return progress;
  }

  const image = getUploadedImageByAssetId(assetId);
  return image?.uploadStatus === 'done' ? 100 : 0;
};

const syncUploadedAssetsLibrary = async () => {
  if (!authUser.value || !assetsIndexEndpoint.value) {
    return;
  }

  try {
    const response = await axios.get(assetsIndexEndpoint.value);
    const assets = Array.isArray(response.data?.assets) ? response.data.assets : [];

    assets.forEach((asset) => {
      upsertUploadedImage({
        id: String(asset.id),
        assetId: String(asset.id),
        label: asset.label || 'Imagen',
        src: asset.url,
        pendingDataUrl: null,
        storagePath: asset.path,
        uploadStatus: 'done',
        needsUpload: false,
        errorMessage: null,
        intrinsicWidth: asset.width ?? null,
        intrinsicHeight: asset.height ?? null,
      });
    });
  } catch (error) {
    console.error('No se pudo cargar la librería de imágenes del usuario', error);
  }
};

const humanizeUploadError = (error) => {
  const status = error?.response?.status;
  if (status === 413 || status === 422) {
    return 'La imagen es demasiado grande o no tiene un formato válido.';
  }

  return 'No se pudo subir la imagen. Reintenta.';
};

const getImageIntrinsicSize = (src) => new Promise((resolve) => {
  if (!src) {
    resolve(null);
    return;
  }

  const image = new Image();
  image.onload = () => {
    resolve({
      width: image.naturalWidth || image.width,
      height: image.naturalHeight || image.height,
    });
  };
  image.onerror = () => resolve(null);
  image.src = src;
});

const buildInitialImageLayout = async (src) => {
  const bounds = getCanvasBounds();
  const fallbackWidth = 220;
  const fallbackHeight = 160;
  const intrinsicSize = await getImageIntrinsicSize(src);

  if (!intrinsicSize?.width || !intrinsicSize?.height) {
    return {
      intrinsicSize: null,
      layout: buildDefaultLayout({
        w: fallbackWidth,
        h: fallbackHeight,
        x: getInsertX(fallbackWidth),
        y: 120,
        backgroundColor: '#ffffff',
        color: '#ffffff',
      }),
    };
  }

  const maxWidth = Math.max(120, bounds.width - 48);
  const maxHeight = Math.max(120, bounds.height - 72);
  const scale = Math.min(1, maxWidth / intrinsicSize.width, maxHeight / intrinsicSize.height);
  const width = Math.max(40, Math.round(intrinsicSize.width * scale));
  const height = Math.max(40, Math.round(intrinsicSize.height * scale));

  return {
    intrinsicSize,
    layout: buildDefaultLayout({
      w: width,
      h: height,
      x: getInsertX(width),
      y: 120,
      backgroundColor: '#ffffff',
      color: '#ffffff',
      imageCropScale: 1,
      imageCropOffsetX: 0,
      imageCropOffsetY: 0,
      flipX: false,
      flipY: false,
    }),
  };
};

const addImageElementFromSrc = async (src, label = 'Imagen', options = {}) => {
  activateVisibleDocumentPage();
  if (!src) return;
  const {
    assetId = null,
    pendingDataUrl = null,
    storagePath = null,
    needsUpload = false,
    closePanel = true,
    layoutOverrides = {},
    intrinsicWidth = null,
    intrinsicHeight = null,
  } = options;

  const id = createElementId('image');
  const { layout: baseLayout, intrinsicSize } = await buildInitialImageLayout(src);
  const layout = {
    ...baseLayout,
    ...layoutOverrides,
  };

  placeInsideCanvas(layout);
  state.customElements = {
    ...(state.customElements ?? {}),
    [id]: {
      id,
      type: 'image',
      label,
      src,
      assetId,
      pendingDataUrl,
      storagePath,
      needsUpload,
      intrinsicWidth: intrinsicWidth ?? intrinsicSize?.width ?? null,
      intrinsicHeight: intrinsicHeight ?? intrinsicSize?.height ?? null,
    },
  };
  state.elementLayout = {
    ...(state.elementLayout ?? {}),
    [id]: layout,
  };
  state.selectedElementId = id;
  if (closePanel) {
    closeImagePanel();
  }
  return id;
};

const clearBackgroundImage = () => {
  state.elementLayout.background = {
    ...state.elementLayout.background,
    backgroundImageSrc: null,
    backgroundImageAssetId: null,
    backgroundImagePendingDataUrl: null,
    backgroundImageStoragePath: null,
    backgroundImageWidth: null,
    backgroundImageHeight: null,
    backgroundImageCropScale: 1,
    backgroundImageCropOffsetX: 0,
    backgroundImageCropOffsetY: 0,
    backgroundImageFlipX: false,
    backgroundImageFlipY: false,
    backgroundImageOpacity: 100,
    backgroundImageTransparencyType: 'flat',
    backgroundImageTransparencyFadeOpacity: 0,
    backgroundImageTransparencyCenterX: 50,
    backgroundImageTransparencyCenterY: 50,
    backgroundImageTransparencyRadius: 70,
    backgroundImageTransparencyRadiusX: 70,
    backgroundImageTransparencyRadiusY: 45,
    backgroundImageTransparencyRotation: 0,
    backgroundImageTransparencyStartX: 0,
    backgroundImageTransparencyStartY: 50,
    backgroundImageTransparencyEndX: 100,
    backgroundImageTransparencyEndY: 50,
    backgroundImageTransparencyEasing: 'linear',
  };
};

const clearBackgroundFill = () => {
  state.elementLayout.background = {
    ...state.elementLayout.background,
    fillMode: 'solid',
    backgroundColor: '#ffffff',
    gradientStart: '#0ea5e9',
    gradientEnd: '#8b5cf6',
    gradientAngle: 135,
  };
};

const setBackgroundImage = async ({
  src,
  assetId = null,
  label = 'Fondo',
  pendingDataUrl = null,
  storagePath = null,
  needsUpload = false,
  intrinsicWidth = null,
  intrinsicHeight = null,
}) => {
  if (!src) return;

  const intrinsicSize = intrinsicWidth && intrinsicHeight
    ? { width: intrinsicWidth, height: intrinsicHeight }
    : await getImageIntrinsicSize(src);

  state.elementLayout.background = {
    ...state.elementLayout.background,
    backgroundImageSrc: src,
    backgroundImageAssetId: assetId,
    backgroundImagePendingDataUrl: pendingDataUrl,
    backgroundImageStoragePath: storagePath,
    backgroundImageWidth: intrinsicSize?.width ?? null,
    backgroundImageHeight: intrinsicSize?.height ?? null,
    backgroundImageCropScale: 1,
    backgroundImageCropOffsetX: 0,
    backgroundImageCropOffsetY: 0,
    backgroundImageFlipX: false,
    backgroundImageFlipY: false,
    backgroundImageOpacity: 100,
    backgroundImageTransparencyType: 'flat',
    backgroundImageTransparencyFadeOpacity: 0,
    backgroundImageTransparencyCenterX: 50,
    backgroundImageTransparencyCenterY: 50,
    backgroundImageTransparencyRadius: 70,
    backgroundImageTransparencyRadiusX: 70,
    backgroundImageTransparencyRadiusY: 45,
    backgroundImageTransparencyRotation: 0,
    backgroundImageTransparencyStartX: 0,
    backgroundImageTransparencyStartY: 50,
    backgroundImageTransparencyEndX: 100,
    backgroundImageTransparencyEndY: 50,
    backgroundImageTransparencyEasing: 'linear',
  };

  state.selectedElementId = 'background';
  activePropertyPanel.value = 'color';
  optionsPanelOpen.value = true;
  imagePanelOpen.value = false;
  textPanelOpen.value = false;
  shapePanelOpen.value = false;

  if (assetId) {
    upsertUploadedImage({
      assetId,
      label,
      src,
      pendingDataUrl,
      storagePath,
      needsUpload,
      uploadStatus: needsUpload ? 'pending' : 'done',
      intrinsicWidth: intrinsicSize?.width ?? null,
      intrinsicHeight: intrinsicSize?.height ?? null,
    });
  }
};

const replaceUploadedImageSourceEverywhere = async ({ assetId, finalUrl, storagePath = null, canonicalAssetId = null }) => {
  const nextAssetId = canonicalAssetId ? String(canonicalAssetId) : assetId;
  const uploadedImage = getUploadedImageByAssetId(assetId);
  const previousSrc = uploadedImage?.pendingDataUrl || uploadedImage?.src || null;

  await mutateWithoutHistory(() => {
    const previousIndex = getUploadedImageIndexByAssetId(assetId);
    const canonicalIndex = nextAssetId !== assetId ? getUploadedImageIndexByAssetId(nextAssetId) : previousIndex;
    const mergedImage = {
      ...(canonicalIndex >= 0 ? state.userUploadedImages[canonicalIndex] : {}),
      ...(previousIndex >= 0 ? state.userUploadedImages[previousIndex] : {}),
      id: nextAssetId,
      assetId: nextAssetId,
      src: finalUrl,
      pendingDataUrl: null,
      storagePath,
      uploadStatus: 'done',
      needsUpload: false,
      errorMessage: null,
    };

    if (canonicalIndex >= 0) {
      state.userUploadedImages.splice(canonicalIndex, 1, mergedImage);
      if (previousIndex >= 0 && previousIndex !== canonicalIndex) {
        state.userUploadedImages.splice(previousIndex > canonicalIndex ? previousIndex - 1 : previousIndex, 1);
      }
    } else if (previousIndex >= 0) {
      state.userUploadedImages.splice(previousIndex, 1, mergedImage);
    } else {
      upsertUploadedImage(mergedImage);
    }

    Object.entries(state.customElements ?? {}).forEach(([id, element]) => {
      if (!element || element.type !== 'image') return;
      if (element.assetId !== assetId) return;

      state.customElements[id] = {
        ...element,
        assetId: nextAssetId,
        src: finalUrl,
        pendingDataUrl: null,
        storagePath,
        needsUpload: false,
      };
    });

    if (state.elementLayout.background?.backgroundImageAssetId === assetId) {
      state.elementLayout.background = {
        ...state.elementLayout.background,
        backgroundImageAssetId: nextAssetId,
        backgroundImageSrc: finalUrl,
        backgroundImagePendingDataUrl: null,
        backgroundImageStoragePath: storagePath,
      };
    }

    replaceImageAssetSource({
      assetId,
      nextAssetId,
      previousSrc,
      nextSrc: finalUrl,
      storagePath,
    });
  });

  requestImmediateStateFlush();
};

const uploadImageAsset = async ({ assetId, file, label, dataUrl }) => {
  if (!assetId || !file || activeUploadAssetIds.has(assetId)) {
    return;
  }

  activeUploadAssetIds.add(assetId);
  uploadProgressByAssetId[assetId] = Math.max(1, getUploadProgress(assetId));

  updateUploadedImage(assetId, {
    src: dataUrl,
    pendingDataUrl: dataUrl,
    uploadStatus: 'uploading',
    needsUpload: true,
    errorMessage: null,
  });

  try {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('assetId', assetId);
    formData.append('label', label ?? file.name ?? 'Imagen');

    const response = await axios.post(uploadEndpoint.value, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (event) => {
        if (!event.total) return;
        uploadProgressByAssetId[assetId] = Math.min(99, Math.round((event.loaded / event.total) * 100));
      },
    });

    const finalUrl = response.data?.url;
    const storagePath = response.data?.path ?? null;
    const canonicalAssetId = response.data?.assetId ?? null;

    if (!finalUrl) {
      throw new Error('La respuesta del servidor no incluyó la URL de la imagen.');
    }

    uploadProgressByAssetId[assetId] = 100;
    await replaceUploadedImageSourceEverywhere({ assetId, finalUrl, storagePath, canonicalAssetId });
  } catch (error) {
    console.error('No se pudo subir la imagen del usuario', error);
    uploadProgressByAssetId[assetId] = 0;
    updateUploadedImage(assetId, {
      src: dataUrl,
      pendingDataUrl: dataUrl,
      uploadStatus: 'error',
      needsUpload: true,
      errorMessage: humanizeUploadError(error),
    });
  } finally {
    activeUploadAssetIds.delete(assetId);
  }
};

const queueUploadForAsset = async (assetId, options = {}) => {
  if (!assetId || activeUploadAssetIds.has(assetId)) {
    return;
  }

  const uploadedImage = getUploadedImageByAssetId(assetId);
  const label = options.label ?? uploadedImage?.label ?? 'Imagen';
  const pendingDataUrl = options.dataUrl ?? uploadedImage?.pendingDataUrl ?? uploadedImage?.src ?? '';

  if (!isDataImageUrl(pendingDataUrl)) {
    return;
  }

  try {
    const file = options.file ?? dataUrlToFile(pendingDataUrl, label);
    await uploadImageAsset({
      assetId,
      file,
      label,
      dataUrl: pendingDataUrl,
    });
  } catch (error) {
    console.error('No se pudo preparar la reanudación del upload de imagen', error);
    updateUploadedImage(assetId, {
      uploadStatus: 'error',
      needsUpload: true,
      errorMessage: humanizeUploadError(error),
    });
  }
};

const createPendingUploadedImageFromFile = async (file, options = {}) => {
  if (!(file instanceof File) || !file.type.startsWith('image/')) {
    return null;
  }

  const processedFile = await optimizeImageFile(file, imageUploadProcessingConfig.value);
  const dataUrl = await fileToDataUrl(processedFile);
  const intrinsicSize = await getImageIntrinsicSize(dataUrl);
  const assetId = createElementId('upload');
  const label = processedFile.name || file.name || 'Imagen';

  upsertUploadedImage({
    assetId,
    label,
    src: dataUrl,
    pendingDataUrl: dataUrl,
    uploadStatus: 'pending',
    needsUpload: true,
    errorMessage: null,
    intrinsicWidth: intrinsicSize?.width ?? null,
    intrinsicHeight: intrinsicSize?.height ?? null,
  });

  if (options.useAsBackground) {
    await setBackgroundImage({
      src: dataUrl,
      assetId,
      label,
      pendingDataUrl: dataUrl,
      needsUpload: true,
      intrinsicWidth: intrinsicSize?.width ?? null,
      intrinsicHeight: intrinsicSize?.height ?? null,
    });
  } else if (options.insertIntoCanvas) {
    await addImageElementFromSrc(dataUrl, label, {
      assetId,
      pendingDataUrl: dataUrl,
      needsUpload: true,
      closePanel: Boolean(options.closePanel),
      intrinsicWidth: intrinsicSize?.width ?? null,
      intrinsicHeight: intrinsicSize?.height ?? null,
    });
  }

  if (options.openUploadsPanel) {
    optionsPanelOpen.value = true;
    imagePanelOpen.value = true;
    textPanelOpen.value = false;
    shapePanelOpen.value = false;
    imagePanelTab.value = 'uploads';
  }

  queueUploadForAsset(assetId, { file: processedFile, dataUrl, label });
  requestImmediateStateFlush();

  return assetId;
};

const triggerImagePicker = () => {
  imageInputRef.value?.click();
};

const onImagePicked = async (event) => {
  const input = event.target;
  const files = Array.from(input?.files ?? []).filter((file) => file.type.startsWith('image/'));
  if (!files.length) return;

  imagePanelTab.value = 'uploads';
  for (const file of files) {
    // Desde el picker actÃºa como subida a la galería del usuario; la inserción en el diseño queda a elección posterior.
    // eslint-disable-next-line no-await-in-loop
    await createPendingUploadedImageFromFile(file, { openUploadsPanel: true });
  }

  input.value = '';
};

const addImageFromUrl = async () => {
  const src = imageUrlInput.value.trim();
  if (!src) return;

  if (state.selectedElementId === 'background') {
    await setBackgroundImage({ src, label: 'Fondo' });
    return;
  }

  await addImageElementFromSrc(src, 'Imagen URL');
};

const addLibraryImage = async (image) => {
  if (state.selectedElementId === 'background') {
    await setBackgroundImage({
      src: image?.src,
      label: image?.label || 'Fondo',
    });
    return;
  }

  return addImageElementFromSrc(image?.src, image?.label || 'Imagen de libreria');
};

const addUploadedImage = async (image) => {
  const src = image?.src || image?.pendingDataUrl || '';
  if (!src) return;

  if (state.selectedElementId === 'background') {
    await setBackgroundImage({
      src,
      assetId: image?.assetId ?? image?.id ?? null,
      label: image?.label || 'Fondo',
      pendingDataUrl: image?.pendingDataUrl ?? (isDataImageUrl(src) ? src : null),
      storagePath: image?.storagePath ?? null,
      needsUpload: Boolean(image?.needsUpload),
      intrinsicWidth: image?.intrinsicWidth ?? null,
      intrinsicHeight: image?.intrinsicHeight ?? null,
    });

    if (image?.needsUpload && (image?.pendingDataUrl || isDataImageUrl(src))) {
      queueUploadForAsset(image.assetId ?? image.id, {
        dataUrl: image.pendingDataUrl ?? src,
        label: image.label,
      });
    }
    return;
  }

  await addImageElementFromSrc(src, image?.label || 'Imagen subida', {
    assetId: image?.assetId ?? image?.id ?? null,
    pendingDataUrl: image?.pendingDataUrl ?? (isDataImageUrl(src) ? src : null),
    storagePath: image?.storagePath ?? null,
    needsUpload: Boolean(image?.needsUpload),
    intrinsicWidth: image?.intrinsicWidth ?? null,
    intrinsicHeight: image?.intrinsicHeight ?? null,
  });

  if (image?.needsUpload && (image?.pendingDataUrl || isDataImageUrl(src))) {
    queueUploadForAsset(image.assetId ?? image.id, {
      dataUrl: image.pendingDataUrl ?? src,
      label: image.label,
    });
  }
};

const retryUploadedImage = (image) => {
  const assetId = image?.assetId ?? image?.id ?? null;
  const pendingDataUrl = image?.pendingDataUrl ?? image?.src ?? '';
  if (!assetId || !isDataImageUrl(pendingDataUrl)) return;

  queueUploadForAsset(assetId, {
    dataUrl: pendingDataUrl,
    label: image?.label ?? 'Imagen',
  });
};

const toggleSelectedImageFlip = (axis) => {
  if (state.selectedElementId === 'background') {
    if (!backgroundHasImage.value) return;
    const key = axis === 'x' ? 'backgroundImageFlipX' : 'backgroundImageFlipY';
    const offsetKey = axis === 'x' ? 'backgroundImageCropOffsetX' : 'backgroundImageCropOffsetY';
    state.elementLayout.background[key] = !state.elementLayout.background[key];
    state.elementLayout.background[offsetKey] = Number(state.elementLayout.background[offsetKey] ?? 0) * -1;
    return;
  }

  if (selectedElementType.value !== 'image' || !selectedElement.value) return;
  const key = axis === 'x' ? 'flipX' : 'flipY';
  const offsetKey = axis === 'x' ? 'imageCropOffsetX' : 'imageCropOffsetY';
  selectedElement.value[key] = !selectedElement.value[key];
  selectedElement.value[offsetKey] = Number(selectedElement.value[offsetKey] ?? 0) * -1;
};

const resetSelectedImageCrop = () => {
  if (state.selectedElementId === 'background') {
    if (!backgroundHasImage.value) return;
    state.elementLayout.background.backgroundImageCropScale = 1;
    state.elementLayout.background.backgroundImageCropOffsetX = 0;
    state.elementLayout.background.backgroundImageCropOffsetY = 0;
    return;
  }

  if (selectedElementType.value !== 'image' || !selectedElement.value) return;
  selectedElement.value.imageCropScale = 1;
  selectedElement.value.imageCropOffsetX = 0;
  selectedElement.value.imageCropOffsetY = 0;
};

const detachBackgroundImage = async () => {
  if (!backgroundHasImage.value) return;

  const backgroundLayout = state.elementLayout.background ?? {};
  const width = Math.round(editorCanvasDimensions.value.width * 0.75);
  const height = Math.round(editorCanvasDimensions.value.height * 0.75);
  const src = backgroundLayout.backgroundImageSrc;

  clearBackgroundImage();

  await addImageElementFromSrc(src, 'Imagen separada del fondo', {
    assetId: backgroundLayout.backgroundImageAssetId ?? null,
    pendingDataUrl: backgroundLayout.backgroundImagePendingDataUrl ?? null,
    storagePath: backgroundLayout.backgroundImageStoragePath ?? null,
    needsUpload: Boolean(backgroundLayout.backgroundImagePendingDataUrl),
    intrinsicWidth: backgroundLayout.backgroundImageWidth ?? null,
    intrinsicHeight: backgroundLayout.backgroundImageHeight ?? null,
    layoutOverrides: {
      w: width,
      h: height,
      x: Math.max(0, Math.round((editorCanvasDimensions.value.width - width) / 2)),
      y: Math.max(18, Math.round((editorCanvasDimensions.value.height - height) / 2)),
      imageCropScale: backgroundLayout.backgroundImageCropScale ?? 1,
      imageCropOffsetX: backgroundLayout.backgroundImageCropOffsetX ?? 0,
      imageCropOffsetY: backgroundLayout.backgroundImageCropOffsetY ?? 0,
      flipX: Boolean(backgroundLayout.backgroundImageFlipX),
      flipY: Boolean(backgroundLayout.backgroundImageFlipY),
      opacity: Number(backgroundLayout.backgroundImageOpacity ?? 100),
      transparencyType: backgroundLayout.backgroundImageTransparencyType ?? 'flat',
      transparencyFadeOpacity: Number(backgroundLayout.backgroundImageTransparencyFadeOpacity ?? 0),
      transparencyCenterX: Number(backgroundLayout.backgroundImageTransparencyCenterX ?? 50),
      transparencyCenterY: Number(backgroundLayout.backgroundImageTransparencyCenterY ?? 50),
      transparencyRadius: Number(backgroundLayout.backgroundImageTransparencyRadius ?? 70),
      transparencyRadiusX: Number(backgroundLayout.backgroundImageTransparencyRadiusX ?? 70),
      transparencyRadiusY: Number(backgroundLayout.backgroundImageTransparencyRadiusY ?? 45),
      transparencyRotation: Number(backgroundLayout.backgroundImageTransparencyRotation ?? 0),
      transparencyStartX: Number(backgroundLayout.backgroundImageTransparencyStartX ?? 0),
      transparencyStartY: Number(backgroundLayout.backgroundImageTransparencyStartY ?? 50),
      transparencyEndX: Number(backgroundLayout.backgroundImageTransparencyEndX ?? 100),
      transparencyEndY: Number(backgroundLayout.backgroundImageTransparencyEndY ?? 50),
      transparencyEasing: backgroundLayout.backgroundImageTransparencyEasing ?? 'linear',
    },
  });
};

const clearBackgroundCompletely = () => {
  clearBackgroundImage();
  clearBackgroundFill();
  state.selectedElementId = 'background';
  activePropertyPanel.value = 'color';
  optionsPanelOpen.value = true;
};

const promoteSelectedImageToBackground = async () => {
  if (selectedElementType.value !== 'image' || !state.selectedElementId || !selectedElement.value) {
    return;
  }

  if (backgroundHasImage.value) {
    const confirmed = window.confirm('Ya hay una imagen de fondo. Si continÃºas, será reemplazada por la imagen seleccionada.');
    if (!confirmed) {
      return;
    }
  }

  const elementId = state.selectedElementId;
  const imageElement = state.customElements?.[elementId];
  const imageLayout = state.elementLayout?.[elementId];

  if (!imageElement || !imageLayout) {
    return;
  }

  await setBackgroundImage({
    src: imageElement.src,
    assetId: imageElement.assetId ?? null,
    label: imageElement.label ?? 'Fondo',
    pendingDataUrl: imageElement.pendingDataUrl ?? null,
    storagePath: imageElement.storagePath ?? null,
    needsUpload: Boolean(imageElement.needsUpload),
    intrinsicWidth: imageElement.intrinsicWidth ?? null,
    intrinsicHeight: imageElement.intrinsicHeight ?? null,
  });

  state.elementLayout.background = {
    ...state.elementLayout.background,
    backgroundImageCropScale: Math.max(1, Number(imageLayout.imageCropScale ?? 1)),
    backgroundImageCropOffsetX: Number(imageLayout.imageCropOffsetX ?? 0),
    backgroundImageCropOffsetY: Number(imageLayout.imageCropOffsetY ?? 0),
    backgroundImageFlipX: Boolean(imageLayout.flipX),
    backgroundImageFlipY: Boolean(imageLayout.flipY),
    backgroundImageOpacity: Number(imageLayout.opacity ?? 100),
    backgroundImageTransparencyType: imageLayout.transparencyType ?? 'flat',
    backgroundImageTransparencyFadeOpacity: Number(imageLayout.transparencyFadeOpacity ?? 0),
    backgroundImageTransparencyCenterX: Number(imageLayout.transparencyCenterX ?? 50),
    backgroundImageTransparencyCenterY: Number(imageLayout.transparencyCenterY ?? 50),
    backgroundImageTransparencyRadius: Number(imageLayout.transparencyRadius ?? 70),
    backgroundImageTransparencyRadiusX: Number(imageLayout.transparencyRadiusX ?? 70),
    backgroundImageTransparencyRadiusY: Number(imageLayout.transparencyRadiusY ?? 45),
    backgroundImageTransparencyRotation: Number(imageLayout.transparencyRotation ?? 0),
    backgroundImageTransparencyStartX: Number(imageLayout.transparencyStartX ?? 0),
    backgroundImageTransparencyStartY: Number(imageLayout.transparencyStartY ?? 50),
    backgroundImageTransparencyEndX: Number(imageLayout.transparencyEndX ?? 100),
    backgroundImageTransparencyEndY: Number(imageLayout.transparencyEndY ?? 50),
    backgroundImageTransparencyEasing: imageLayout.transparencyEasing ?? 'linear',
  };

  if (state.customElements?.[elementId]) {
    delete state.customElements[elementId];
  }
  if (state.elementLayout?.[elementId]) {
    delete state.elementLayout[elementId];
  }
  if (elementMeasurements[elementId]) {
    delete elementMeasurements[elementId];
  }
  if (richEditorRefs.value[elementId]) {
    delete richEditorRefs.value[elementId];
  }
};

const handlePropertyTabClick = async (tab) => {
  if (!tab) return;

  if (tab.id === 'detach') {
    await detachBackgroundImage();
    return;
  }

  if (tab.id === 'set-as-background') {
    await promoteSelectedImageToBackground();
    return;
  }

  if (tab.id === 'clear-background') {
    clearBackgroundCompletely();
    return;
  }

  activePropertyPanel.value = tab.id;
  optionsPanelOpen.value = true;
};

const syncPendingUploadsFromPersistedState = async () => {
  await mutateWithoutHistory(() => {
    const backgroundImageSrc = state.elementLayout.background?.backgroundImageSrc ?? '';
    const backgroundPendingDataUrl = state.elementLayout.background?.backgroundImagePendingDataUrl
      ?? (isDataImageUrl(backgroundImageSrc) ? backgroundImageSrc : null);
    const backgroundAssetId = state.elementLayout.background?.backgroundImageAssetId
      ?? (backgroundPendingDataUrl ? createElementId('background-upload') : null);

    if (backgroundPendingDataUrl && backgroundAssetId) {
      state.elementLayout.background = {
        ...state.elementLayout.background,
        backgroundImageAssetId: backgroundAssetId,
        backgroundImagePendingDataUrl: backgroundPendingDataUrl,
      };

      if (!getUploadedImageByAssetId(backgroundAssetId)) {
        upsertUploadedImage({
          assetId: backgroundAssetId,
          label: 'Fondo',
          src: backgroundPendingDataUrl,
          pendingDataUrl: backgroundPendingDataUrl,
          uploadStatus: 'pending',
          needsUpload: true,
          intrinsicWidth: state.elementLayout.background?.backgroundImageWidth ?? null,
          intrinsicHeight: state.elementLayout.background?.backgroundImageHeight ?? null,
        });
      }
    }

    Object.entries(state.customElements ?? {}).forEach(([id, element]) => {
      if (!element || element.type !== 'image') return;

      const pendingDataUrl = element.pendingDataUrl ?? (isDataImageUrl(element.src) ? element.src : null);
      const assetId = element.assetId ?? (pendingDataUrl ? createElementId(`recovered-${id}`) : null);

      if (!assetId || !pendingDataUrl) return;

      if (!element.assetId || element.assetId !== assetId) {
        state.customElements[id] = {
          ...element,
          assetId,
          pendingDataUrl,
          needsUpload: true,
        };
      }

      if (!getUploadedImageByAssetId(assetId)) {
        upsertUploadedImage({
          assetId,
          label: element.label ?? 'Imagen recuperada',
          src: pendingDataUrl,
          pendingDataUrl,
          uploadStatus: 'pending',
          needsUpload: true,
        });
      }
    });
  });

  state.userUploadedImages.forEach((image) => {
    const assetId = image.assetId ?? image.id;
    const pendingDataUrl = image.pendingDataUrl ?? (isDataImageUrl(image.src) ? image.src : null);

    if (assetId && pendingDataUrl && (image.needsUpload || image.uploadStatus !== 'done')) {
      queueUploadForAsset(assetId, {
        dataUrl: pendingDataUrl,
        label: image.label,
      });
    }
  });
};

const handleCanvasFileDragOver = (event) => {
  if (!hasFilesInTransfer(event.dataTransfer)) return;

  event.preventDefault();
  fileDragActive.value = true;
  const rect = event.currentTarget?.getBoundingClientRect?.();
  if (rect) {
    const edgeThreshold = Math.min(72, Math.max(40, Math.round(Math.min(rect.width, rect.height) * 0.12)));
    backgroundDropPreview.value = (
      event.clientX - rect.left <= edgeThreshold
      || rect.right - event.clientX <= edgeThreshold
      || event.clientY - rect.top <= edgeThreshold
      || rect.bottom - event.clientY <= edgeThreshold
    );
  }
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'copy';
  }
};

const handleCanvasFileDragEnter = (event) => {
  if (!hasFilesInTransfer(event.dataTransfer)) return;

  event.preventDefault();
  fileDragActive.value = true;
};

const handleCanvasFileDragLeave = (event) => {
  if (event?.currentTarget?.contains?.(event.relatedTarget)) {
    return;
  }

  fileDragActive.value = false;
  backgroundDropPreview.value = false;
};

const handleCanvasFileDrop = async (event) => {
  const files = extractImageFilesFromDataTransfer(event.dataTransfer);
  const shouldUseAsBackground = backgroundDropPreview.value && files.length === 1;
  fileDragActive.value = false;
  backgroundDropPreview.value = false;
  if (!files.length) return;

  event.preventDefault();
  for (const file of files) {
    // eslint-disable-next-line no-await-in-loop
    await createPendingUploadedImageFromFile(file, shouldUseAsBackground
      ? { useAsBackground: true }
      : { insertIntoCanvas: true });
  }
};

const handleDocumentPaste = async (event) => {
  if (editingElementId.value || isEditableTarget(event.target)) {
    return;
  }

  const files = extractImageFilesFromDataTransfer(event.clipboardData);
  if (!files.length) return;

  event.preventDefault();
  for (const file of files) {
    // eslint-disable-next-line no-await-in-loop
    await createPendingUploadedImageFromFile(file, { insertIntoCanvas: true });
  }
};

const addShapeElement = (shapeKind) => {
  activateVisibleDocumentPage();
  const shape = shapePresets.find((item) => item.id === shapeKind);
  if (!shape) return;

  const isRectangle = shapeKind === 'rectangle' || shapeKind === 'rectangle-outline';
  const layout = buildDefaultLayout({
    // El rectángulo base nace cuadrado; luego el usuario puede deformarlo libremente.
    w: isRectangle ? 140 : 140,
    h: isRectangle ? 140 : 140,
    x: getInsertX(140),
    y: 150,
    backgroundColor: '#38bdf8',
    opacity: 100,
    shadow: true,
    border: false,
    contourWidth: 0,
    contourColor: '#000000',
  });
  placeInsideCanvas(layout);

  const id = createElementId('shape');
  state.customElements = {
    ...(state.customElements ?? {}),
    [id]: {
    id,
    type: 'shape',
    label: shape.label,
    shapeKind,
    },
  };
  state.elementLayout = {
    ...(state.elementLayout ?? {}),
    [id]: layout,
  };
  state.selectedElementId = id;
};

const getEstimatedTextHeight = (layout, text = '') => ensureParagraphStyles(layout, text)
    .reduce((total, style) => total + Math.max((style.fontSize ?? layout.fontSize ?? 16) * (style.lineHeight ?? 1.3), 16), 0);

const updateElementMeasurement = (id, node) => {
    if (!node) return;

    elementMeasurements[id] = {
        width: node.offsetWidth,
        height: node.offsetHeight,
    };

    if (isTextElement(id) && !isLinkedTextElement(id)) {
        const layout = state.elementLayout[id];
        if (layout && layout.h !== node.offsetHeight) {
            layout.h = node.offsetHeight;
        }
    }
};

  const cloneSelectedElement = () => {
    const sourceId = state.selectedElementId;
    if (!sourceId || sourceId === 'background' || isTemplateFieldElement(sourceId)) return;

    if (editingElementId.value) {
      commitTextEdit();
    }

    const sourceLayout = state.elementLayout[sourceId];
    const sourceElement = editorElements.value.find((item) => item.id === sourceId);
    if (!sourceLayout || !sourceElement) return;

    const cloneId = createElementId(sourceElement.type || 'element');
    const oldNextId = sourceElement.type === 'linkedText' ? (sourceLayout.linkedTextNext ?? null) : null;
    const linkedTextGroupId = sourceElement.type === 'linkedText'
      ? (sourceLayout.linkedTextGroupId || `linked-group-${Date.now()}`)
      : null;
    const cloneLayout = {
      ...sourceLayout,
      x: (sourceLayout.x ?? 0) + 18,
      y: (sourceLayout.y ?? 0) + 18,
      zIndex: getMaxZIndex() + 10,
      paragraphStyles: Array.isArray(sourceLayout.paragraphStyles)
        ? sourceLayout.paragraphStyles.map((style) => ({ ...style }))
        : undefined,
    };

    placeInsideCanvas(cloneLayout);

    if (sourceElement.type === 'linkedText') {
      sourceLayout.linkedTextGroupId = linkedTextGroupId;
      sourceLayout.linkedTextNext = cloneId;

      cloneLayout.linkedTextGroupId = linkedTextGroupId;
      cloneLayout.linkedTextPrev = sourceId;
      cloneLayout.linkedTextNext = oldNextId;

      if (oldNextId && linkedTextLayoutFromAnyPage(oldNextId)) {
        linkedTextSetLayoutField(oldNextId, 'linkedTextPrev', cloneId);
        linkedTextSetLayoutField(oldNextId, 'linkedTextGroupId', linkedTextGroupId);
      }

      state.customElements[cloneId] = {
        id: cloneId,
        type: 'linkedText',
        label: `${sourceElement.label} continuación`,
        text: '',
      };
    } else if (sourceElement.type === 'text') {
      state.customElements[cloneId] = {
        type: 'text',
        label: `${sourceElement.label} copia`,
        text: getElementText(sourceId),
        fieldKey: sourceElement.fieldKey ?? null,
      };
    } else if (sourceElement.type === 'image') {
      state.customElements[cloneId] = {
        type: 'image',
        label: `${sourceElement.label} copia`,
        src: sourceElement.src,
        assetId: sourceElement.assetId ?? null,
        pendingDataUrl: sourceElement.pendingDataUrl ?? null,
        storagePath: sourceElement.storagePath ?? null,
        needsUpload: Boolean(sourceElement.needsUpload),
      };
    } else if (sourceElement.type === 'shape') {
      state.customElements[cloneId] = {
        type: 'shape',
        label: `${sourceElement.label} copia`,
        shapeKind: sourceElement.shapeKind,
      };
    } else {
      return;
    }

    state.elementLayout[cloneId] = cloneLayout;
    state.selectedElementId = cloneId;

    if (sourceElement.type === 'linkedText') {
      const headId = getLinkedTextChainHead(sourceId);
      const chain = getLinkedTextChain(headId);
      chain.forEach((item, index) => {
        item.layout.linkedTextChainIndex = index;
        item.layout.linkedTextGroupId = linkedTextGroupId;
      });
      recalculateLinkedTextAllocations(headId);
    }
  };

const removeLinkedTextFromChain = (id) => {
    const layout = linkedTextLayoutFromAnyPage(id);
    if (!layout || linkedTextElementFromAnyPage(id)?.type !== 'linkedText') return;

    const prevId = layout.linkedTextPrev;
    const nextId = layout.linkedTextNext;

    if (prevId && linkedTextLayoutFromAnyPage(prevId)) {
      linkedTextSetLayoutField(prevId, 'linkedTextNext', nextId);
    }
    if (nextId && linkedTextLayoutFromAnyPage(nextId)) {
      linkedTextSetLayoutField(nextId, 'linkedTextPrev', prevId);
    }

    const headElement = linkedTextElementFromAnyPage(id);
    if (!prevId && nextId) {
      const nextElement = linkedTextElementFromAnyPage(nextId);
      if (headElement?.type === 'linkedText' && nextElement?.type === 'linkedText') {
        linkedTextSetElementField(nextId, 'html', headElement.html || headElement.text || '');
        linkedTextSetElementField(nextId, 'text', headElement.text || '');
        recalculateLinkedTextAllocations(nextId);
      }
    } else if (prevId) {
      const headId = getLinkedTextChainHead(prevId);
      recalculateLinkedTextAllocations(headId);
    }

    const groupId = layout.linkedTextGroupId;
    if (groupId) {
      const system = linkedTextBoxSystem.getOrCreateSystem(groupId);
      if (system?.fragments?.[id]) {
        delete system.fragments[id];
      }
    }
  };

  const deleteSelectedElement = () => {
    const id = state.selectedElementId;
    if (!id) return;
    if (id === 'background') {
      clearBackgroundCompletely();
      return;
    }

    if (editingElementId.value === id) {
      commitTextEdit();
    }

    removeLinkedTextFromChain(id);

    clearContentForRemovedTextElement(id);

    if (state.customElements?.[id]) {
      delete state.customElements[id];
    }

    if (state.elementLayout?.[id]) {
      delete state.elementLayout[id];
    }

    if (elementMeasurements[id]) {
      delete elementMeasurements[id];
    }

    if (richEditorRefs.value[id]) {
      delete richEditorRefs.value[id];
    }

    state.selectedElementId = null;
    activePropertyPanel.value = null;
  };

const cloneElementsByIds = (ids) => {
    const clonedIds = [];

    ids.forEach((sourceId) => {
      const sourceLayout = state.elementLayout[sourceId];
      const sourceElement = editorElements.value.find((item) => item.id === sourceId);
      if (!sourceLayout || !sourceElement || isTemplateFieldElement(sourceId)) return;

      const cloneId = createElementId(sourceElement.type || 'element');
      const cloneLayout = {
        ...sourceLayout,
        x: (sourceLayout.x ?? 0) + 18,
        y: (sourceLayout.y ?? 0) + 18,
        zIndex: getMaxZIndex() + 10,
        paragraphStyles: Array.isArray(sourceLayout.paragraphStyles)
          ? sourceLayout.paragraphStyles.map((style) => ({ ...style }))
          : undefined,
      };

      placeInsideCanvas(cloneLayout);

      if (sourceElement.type === 'text') {
        state.customElements[cloneId] = {
          type: 'text',
          label: `${sourceElement.label} copia`,
          text: getElementText(sourceId),
          fieldKey: sourceElement.fieldKey ?? null,
        };
      } else if (sourceElement.type === 'image') {
        state.customElements[cloneId] = {
          type: 'image',
          label: `${sourceElement.label} copia`,
          src: sourceElement.src,
          assetId: sourceElement.assetId ?? null,
          pendingDataUrl: sourceElement.pendingDataUrl ?? null,
          storagePath: sourceElement.storagePath ?? null,
          needsUpload: Boolean(sourceElement.needsUpload),
        };
      } else if (sourceElement.type === 'shape') {
        state.customElements[cloneId] = {
          type: 'shape',
          label: `${sourceElement.label} copia`,
          shapeKind: sourceElement.shapeKind,
        };
      } else if (sourceElement.type === 'linkedText') {
        const cloneGroupId = `linked-group-${Date.now()}`;
        cloneLayout.linkedTextGroupId = cloneGroupId;
        cloneLayout.linkedTextNext = null;
        cloneLayout.linkedTextPrev = null;
        cloneLayout.linkedTextChainIndex = 0;
        state.customElements[cloneId] = {
          id: cloneId,
          type: 'linkedText',
          label: `${sourceElement.label} copia`,
          text: sourceElement.text ?? '',
          html: sourceElement.html ?? '',
        };
      } else {
        return;
      }

      state.elementLayout[cloneId] = cloneLayout;
      clonedIds.push(cloneId);
    });

    return clonedIds;
  };

  const selectedElementIdsForClipboard = () => {
    if (isGroupSelection.value) return [...(selectedGroup.value?.elementIds ?? [])];
    if (multiSelectionIds.value.length > 1) return [...multiSelectionIds.value];
    return state.selectedElementId && state.selectedElementId !== 'background'
      ? [state.selectedElementId]
      : [];
  };

  const elementSnapshotForClipboard = (sourceId) => {
    const sourceLayout = state.elementLayout[sourceId];
    const sourceElement = editorElements.value.find((item) => item.id === sourceId);
    if (!sourceLayout || !sourceElement) return null;

    return {
      layout: clonePlain(sourceLayout),
      element: {
        ...(state.customElements?.[sourceId] ?? {}),
        id: sourceId,
        type: sourceElement.type,
        label: sourceElement.label ?? 'Elemento',
        text: sourceElement.type === 'text' ? getElementText(sourceId) : undefined,
        fieldKey: sourceElement.fieldKey ?? state.customElements?.[sourceId]?.fieldKey ?? null,
        src: sourceElement.src ?? state.customElements?.[sourceId]?.src ?? null,
        shapeKind: sourceElement.shapeKind ?? state.customElements?.[sourceId]?.shapeKind ?? null,
      },
    };
  };

  const copyCurrentSelection = () => {
    const ids = selectedElementIdsForClipboard();
    const snapshots = ids
      .map((id) => elementSnapshotForClipboard(id))
      .filter(Boolean);

    if (!snapshots.length) return false;

    copiedElements.value = snapshots;
    return true;
  };

  const pasteCopiedElements = async () => {
    if (!copiedElements.value.length) return false;
    if (editingElementId.value) {
      commitTextEdit();
    }

    activateVisibleDocumentPage();
    const pastedIds = [];

    copiedElements.value.forEach(({ element, layout }) => {
      const cloneId = createElementId(element.type || 'element');
      const cloneLayout = {
        ...clonePlain(layout),
        x: layout.x ?? 0,
        y: layout.y ?? 0,
        zIndex: getMaxZIndex() + 10,
        paragraphStyles: Array.isArray(layout.paragraphStyles)
          ? layout.paragraphStyles.map((style) => ({ ...style }))
          : undefined,
      };
      placeInsideCanvas(cloneLayout);

      if (element.type === 'text') {
        state.customElements[cloneId] = {
          type: 'text',
          label: element.label ? `${element.label} copia` : 'Texto copia',
          text: element.text ?? '',
          fieldKey: element.fieldKey ?? null,
        };
      } else if (element.type === 'image') {
        state.customElements[cloneId] = {
          ...element,
          id: cloneId,
          type: 'image',
          label: element.label ? `${element.label} copia` : 'Imagen copia',
        };
      } else if (element.type === 'shape') {
        state.customElements[cloneId] = {
          type: 'shape',
          label: element.label ? `${element.label} copia` : 'Figura copia',
          shapeKind: element.shapeKind,
        };
      } else {
        return;
      }

      state.elementLayout[cloneId] = cloneLayout;
      pastedIds.push(cloneId);
    });

    if (!pastedIds.length) return false;
    if (pastedIds.length === 1) {
      state.selectedElementId = pastedIds[0];
      multiSelectionIds.value = [];
    } else {
      state.selectedElementId = null;
      multiSelectionIds.value = pastedIds;
    }
    selectedGroupId.value = null;
    await nextTick();
    return true;
  };

  const groupSelectedElements = () => {
    if (multiSelectionIds.value.length < 2) return;

    const ids = [...new Set(multiSelectionIds.value)].filter((id) => state.elementLayout[id]);
    if (ids.length < 2) return;
    if (ids.some((id) => getGroupIdForElement(id))) return;

    const bounds = getSelectionBounds(ids);
    if (!bounds) return;

    const groupId = createElementId('group');
    groupedElements[groupId] = {
      id: groupId,
      elementIds: ids,
      layout: {
        x: bounds.x,
        y: bounds.y,
        w: bounds.w,
        h: bounds.h,
        rotation: 0,
      },
    };

    selectGroup(groupId);
  };

  const cloneCurrentSelection = () => {
    if (isGroupSelection.value) {
      const sourceIds = [...selectedGroup.value.elementIds];
      const clonedIds = cloneElementsByIds(sourceIds);
      if (clonedIds.length < 2) return;
      selectedGroupId.value = null;
      multiSelectionIds.value = clonedIds;
      state.selectedElementId = null;
      groupSelectedElements();
      return;
    }

    if (multiSelectionIds.value.length > 1) {
      const clonedIds = cloneElementsByIds(multiSelectionIds.value);
      if (!clonedIds.length) return;
      if (clonedIds.length === 1) {
        state.selectedElementId = clonedIds[0];
        multiSelectionIds.value = [];
      } else {
        state.selectedElementId = null;
        multiSelectionIds.value = clonedIds;
      }
      return;
    }

    cloneSelectedElement();
  };

  const deleteElementsByIds = (ids) => {
    ids.forEach((id) => {
      if (editingElementId.value === id) {
        commitTextEdit();
      }
      removeLinkedTextFromChain(id);
      clearContentForRemovedTextElement(id);
      if (state.customElements?.[id]) {
        delete state.customElements[id];
      }
      if (state.elementLayout?.[id]) {
        delete state.elementLayout[id];
      }
      if (elementMeasurements[id]) {
        delete elementMeasurements[id];
      }
      if (richEditorRefs.value[id]) {
        delete richEditorRefs.value[id];
      }
    });
  };

  const deleteCurrentSelection = () => {
    if (isGroupSelection.value) {
      deleteElementsByIds(selectedGroup.value.elementIds);
      delete groupedElements[selectedGroupId.value];
      selectedGroupId.value = null;
      return;
    }

    if (multiSelectionIds.value.length > 1) {
      deleteElementsByIds(multiSelectionIds.value);
      multiSelectionIds.value = [];
      return;
    }

    deleteSelectedElement();
  };

  const editSelectedTextElement = () => {
    if (!state.selectedElementId || selectedElementType.value !== 'text') return;
    beginTextEdit(state.selectedElementId, true);
  };

const refreshElementObservers = async () => {
    await nextTick();

    elementObservers.forEach((observer) => observer.disconnect());
    elementObservers.clear();

    if (!canvasRef.value) {
        return;
    }

    editorElements.value.forEach((item) => {
        const node = canvasRef.value.querySelector(`[data-editor-id="${item.id}"]`);

        if (!node) {
            delete elementMeasurements[item.id];
            return;
        }

        updateElementMeasurement(item.id, node);

        const observer = new ResizeObserver(() => {
            updateElementMeasurement(item.id, node);
        });

        observer.observe(node);
        elementObservers.set(item.id, observer);
    });
};

const setDragDocumentState = (active) => {
    document.documentElement.style.userSelect = active ? 'none' : '';
    document.documentElement.style.touchAction = active ? 'none' : '';
};

const startToolbarDrag = (event) => {
    toolbarDrag.active = true;
    toolbarDrag.pointerId = event.pointerId;
    toolbarDrag.startX = event.clientX;
    toolbarDrag.startY = event.clientY;
    toolbarDrag.originX = toolbarPosition.x;
    toolbarDrag.originY = toolbarPosition.y;
    setDragDocumentState(true);
    event.currentTarget?.setPointerCapture?.(event.pointerId);
    event.preventDefault();
};

const getElementText = (id) => {
    switch (id) {
        case 'title':
        case 'subtitle':
        case 'contact':
        case 'extra':
            return state.content[id] ?? '';
        case 'meta':
            return [state.content.date, state.content.time].filter(Boolean).join(' Â· ');
        default:
          return state.customElements?.[id]?.text ?? '';
    }
};

const syncLinkedFieldText = (fieldKey, text) => {
  if (!fieldKey) return;
  Object.entries(state.customElements ?? {}).forEach(([elementId, element]) => {
    if (element?.fieldKey !== fieldKey || !state.elementLayout[elementId]) return;
    element.text = text;
    state.elementLayout[elementId].text = text;
    recalculateTextHeight(elementId);
  });
  if (state.elementLayout[fieldKey]) {
    state.elementLayout[fieldKey].text = text;
    recalculateTextHeight(fieldKey);
  }
};

const updateLinkedContentField = (fieldKey, normalizedText) => {
  switch (fieldKey) {
    case 'title':
    case 'subtitle':
    case 'contact':
    case 'extra':
      state.content[fieldKey] = normalizedText;
      (state.pages ?? []).forEach((page) => {
        page.content = { ...(page.content ?? {}), [fieldKey]: normalizedText };
      });
      syncLinkedFieldText(fieldKey, normalizedText);
      break;
    case 'meta': {
      const parts = normalizedText.split('\n');
      state.content.date = (parts[0] ?? '').trim();
      state.content.time = (parts[1] ?? '').trim();
      (state.pages ?? []).forEach((page) => {
        page.content = {
          ...(page.content ?? {}),
          date: state.content.date,
          time: state.content.time,
        };
      });
      syncLinkedFieldText('meta', normalizedText);
      break;
    }
    default:
      break;
  }
};

const onRichEditorSelectionChange = (id, { paragraphIndex, selectedIndexes }) => {
    if (editingElementId.value !== id) return;

    selectedParagraphIndex.value = clamp(paragraphIndex, 0, Math.max(0, paragraphCount.value - 1));
    paragraphSelection.active = selectedIndexes.length > 1;

    if (paragraphSelection.active) {
        paragraphSelection.start = selectedIndexes[0];
        paragraphSelection.end = selectedIndexes[selectedIndexes.length - 1];
    } else {
        paragraphSelection.start = paragraphIndex;
        paragraphSelection.end = paragraphIndex;
    }
};

const onRichEditorTextUpdate = (id, newText) => {
  const baseTextKeys = ['title', 'subtitle', 'meta', 'contact', 'extra'];
  if (baseTextKeys.includes(id)) {
    if (id === 'meta') {
      const parts = newText.split(' Â· ');
      state.content.date = parts[0] || '';
      state.content.time = parts[1] || '';
    } else {
      state.content[id] = newText;
    }
    recalculateTextHeight(id);
    return;
  }

  if (state.customElements?.[id]?.fieldKey) {
    const linkedFieldKey = state.customElements[id].fieldKey;
    if (linkedFieldKey === 'meta') {
      const parts = newText.split(' Â· ');
      state.content.date = parts[0] || '';
      state.content.time = parts[1] || '';
    } else {
      state.content[linkedFieldKey] = newText;
    }
    recalculateTextHeight(id);
  }

  const element = state.customElements?.[id];
  if (!element) return;

  if (element.type === 'linkedText') {
    return;
  }

  if (element.type === 'text') {
    element.text = newText;
    recalculateTextHeight(id);
  }
};

const recalculateTextHeight = (id) => {
  const layout = state.elementLayout[id];
  if (!layout || !isTextElement(id)) return;
  if (isLinkedTextElement(id)) return;
  const text = getElementText(id);
  const estimatedHeight = getEstimatedTextHeight(layout, text);
  if (estimatedHeight > 0) {
    if (id === 'title' && layout.h !== estimatedHeight) {
      frontendLog.info('title-height', 'Cambio de altura calculado para titulo', {
        id,
        previousHeight: layout.h ?? null,
        nextHeight: estimatedHeight,
        activePageId: activePageId.value,
        editingElementId: editingElementId.value,
        textLength: String(text ?? '').length,
      });
    }
    layout.h = estimatedHeight;
  }
};

const handleClipboardKeydown = async (event) => {
  const targetElement = event.target instanceof Element ? event.target : null;
  if (targetElement?.closest('input, textarea, select, [contenteditable="true"]')) return;
  if (!(event.ctrlKey || event.metaKey) || event.altKey) return;

  const key = event.key.toLowerCase();
  if (key === 'c') {
    if (copyCurrentSelection()) {
      event.preventDefault();
    }
    return;
  }

  if (key === 'v') {
    if (copiedElements.value.length) {
      event.preventDefault();
      await pasteCopiedElements();
    }
  }
};

const onRichEditorStylesUpdate = (id, newStyles) => {
    const element = linkedTextElementFromAnyPage(id);
    if (element?.type === 'linkedText') {
      if (editingElementId.value !== id) return;
      return;
    }

    const styleSourceId = getLinkedTextStyleSourceId(id);
    const layout = linkedTextLayoutFromAnyPage(styleSourceId);
    if (!layout) return;
    linkedTextSetLayoutField(styleSourceId, 'paragraphStyles', newStyles);
};

const {
  clearLongPress,
  handleElementClick,
  markEditorControlInteraction,
  onRichEditorBlur,
  handleElementPointerDown,
  startResize,
  startRotate,
  resetRotation,
  moveDrag,
  endDrag,
  cycleAlignment,
  currentAlignmentIcon,
  changeLayer,
  handleCanvasPointerDown,
  handleGlobalPointerDown,
  handleGlobalKeydown,
  guides,
} = useEditorInteractions({
  state,
  canvasRef,
  richEditorRefs,
  elementMeasurements,
  drag,
  toolbarPosition,
  toolbarDrag,
  touchIntent,
  dragIntent,
  selectionMarquee,
  groupedElements,
  multiSelectionIds,
  selectedGroupId,
  activePropertyPanel,
  paragraphSelection,
  selectedParagraphIndex,
  preserveEditorSelectionUntil,
  suppressElementClickUntil,
  suppressCanvasClickUntil,
  editingElementId,
  zoomScale,
  orderedLayerIds,
  selectedTextStyle,
  commitTextEdit: (...args) => commitTextEdit(...args),
  beginTextEdit: (...args) => beginTextEdit(...args),
  deleteCurrentSelection: () => deleteCurrentSelection(),
  performUndo: () => performUndo(),
  performRedo: () => performRedo(),
  setDragDocumentState: (...args) => setDragDocumentState(...args),
  clearSelection: () => clearSelection(),
  startSelectionMarquee: (...args) => startSelectionMarquee(...args),
  updateSelectionMarqueePreview: () => updateSelectionMarqueePreview(),
  finalizeSelectionMarquee: () => finalizeSelectionMarquee(),
  selectGroup: (...args) => selectGroup(...args),
  getGroupIdForElement: (...args) => getGroupIdForElement(...args),
  buildGroupResizeSnapshot: (...args) => buildGroupResizeSnapshot(...args),
  getSelectionBounds: (...args) => getSelectionBounds(...args),
  getCanvasBounds: () => getCanvasBounds(),
  getEstimatedTextHeight: (...args) => getEstimatedTextHeight(...args),
  getElementText: (...args) => getElementText(...args),
  ensureParagraphStyles: (...args) => ensureParagraphStyles(...args),
  isTextElement: (...args) => isTextElement(...args),
  isLinkedTextElement: (...args) => isLinkedTextElement(...args),
  isAspectLockedResizeElement: (...args) => isAspectLockedResizeElement(...args),
  applyParagraphStyleField: (...args) => applyParagraphStyleField(...args),
  recalculateTextHeight: (...args) => recalculateTextHeight(...args),
  activeSelectionIds,
});

const handleDocumentPointerEnd = async (event) => {
  if (linkedTextLink.active && linkedTextLink.sourceId) {
    const targetId = linkedTextLink.hoverTargetId;
    if (targetId && targetId !== linkedTextLink.sourceId) {
      handleLinkedTextLinkEnd({ event, targetId });
    } else if (!targetId) {
      handleLinkedTextLinkBreak(event);
    }
    linkedTextLink.active = false;
    linkedTextLink.sourceId = null;
    linkedTextLink.hoverTargetId = null;
    event.target?.releasePointerCapture?.(event.pointerId);
  }

  const draggedIds = drag.active && drag.mode === 'multi'
    ? [...multiSelectionIds.value]
    : (drag.active && drag.elementId ? [drag.elementId] : []);
  const wasMoveDrag = drag.active && ['move', 'multi'].includes(drag.mode);
  const sourceSnapshots = wasMoveDrag
    ? draggedIds
        .map((id) => {
          const currentLayout = state.elementLayout[id];
          if (!currentLayout) return null;
          const multiStart = drag.multiSnapshot?.find((item) => item.id === id);
          return {
            id,
            layout: {
              ...clonePlain(currentLayout),
              x: multiStart?.startX ?? (id === drag.elementId ? drag.startX : currentLayout.x),
              y: multiStart?.startY ?? (id === drag.elementId ? drag.startY : currentLayout.y),
            },
            customElement: clonePlain(state.customElements?.[id] ?? null),
          };
        })
        .filter(Boolean)
    : [];
  const sourceBounds = boundsFromLayoutSnapshots(sourceSnapshots);
  const sourceSurfaceRect = wasMoveDrag ? pageSurfaceRect(workingDocumentPageId.value) : null;
  const pointerOffset = sourceBounds && sourceSurfaceRect
    ? {
        x: ((drag.startClientX - sourceSurfaceRect.left) / zoomScale.value) - sourceBounds.x,
        y: ((drag.startClientY - sourceSurfaceRect.top) / zoomScale.value) - sourceBounds.y,
      }
    : null;
  const targetPageId = wasMoveDrag ? pageIdFromPoint(event.clientX, event.clientY) : null;

  endDrag(event);

  if (wasMoveDrag && targetPageId && targetPageId !== workingDocumentPageId.value && sourceSnapshots.length) {
    await transferElementsToPage(draggedIds, targetPageId, event, pointerOffset, sourceSnapshots);
  }
};

const replayClickOnEditor = (id, originalEvent) => {
  if (!originalEvent) return;
  const el = richEditorRefs.value[id]?.$el;
  frontendLog.debug('replayClick', `[${id}] replayClick called: hasEl=${!!el}, clientX=${originalEvent.clientX}, clientY=${originalEvent.clientY}`, {
    hasRef: !!richEditorRefs.value[id],
    hasSetCursor: typeof richEditorRefs.value[id]?.setCursorAtCoords === 'function',
    editingElementId: editingElementId.value,
    elTagName: el?.tagName,
  });

  if (!el) {
    frontendLog.debug('replayClick', `[${id}] No $el found`);
    return;
  }

  const coords = { left: originalEvent.clientX, top: originalEvent.clientY };

  const trySetCursor = () => {
    const editorRef = richEditorRefs.value[id];
    const elNow = editorRef?.$el;
    if (!elNow) {
      frontendLog.debug('replayClick', `[${id}] retry: $el still null`);
      return false;
    }
    const pm = elNow.querySelector('.ProseMirror');
    if (!pm) {
      frontendLog.debug('replayClick', `[${id}] retry: .ProseMirror still null`);
      return false;
    }
    const pmRect = pm.getBoundingClientRect();
    const hasMethod = typeof editorRef?.setCursorAtCoords === 'function';
    frontendLog.debug('replayClick', `[${id}] retry: hasMethod=${hasMethod}, pmRect=${JSON.stringify({x:pmRect.x,y:pmRect.y,w:pmRect.width,h:pmRect.height})}, coords=(${coords.left},${coords.top})`);
    if (!hasMethod) return false;

    editorRef.setCursorAtCoords(coords.left, coords.top);
    return true;
  };

  if (!trySetCursor()) {
    setTimeout(() => trySetCursor(), 300);
  }
};

const beginTextEdit = async (id, focusToEnd = false, clickEvent = null) => {
  if (!isTextElement(id)) return;
  const groupId = getGroupIdForElement(id);
  if (groupId) {
    selectGroup(groupId);
    return;
  }

  if (state.customElements?.[id]?.type === 'linkedText') {
    activeLinkedTextBox.value = id;
    const layout = state.elementLayout[id];
    if (layout?.linkedTextGroupId) {
      linkedTextBoxSystem.startEditing(layout.linkedTextGroupId, id);
    }
  }

    state.selectedElementId = id;
    editingBoxHeight.value = elementMeasurements[id]?.height ?? null;
    selectedParagraphIndex.value = 0;
    paragraphSelection.start = 0;
    paragraphSelection.end = 0;
    paragraphSelection.active = false;
    editingElementId.value = id;
    clearLongPress();
    await nextTick();
    if (focusToEnd) {
      richEditorRefs.value[id]?.focusAtEnd?.();
      return;
    }
    if (state.customElements?.[id]?.type === 'linkedText') {
      if (clickEvent) {
        replayClickOnEditor(id, clickEvent);
      } else {
        richEditorRefs.value[id]?.focusAtPosition?.(0);
      }
      return;
    }
    if (clickEvent) {
      replayClickOnEditor(id, clickEvent);
    } else {
      richEditorRefs.value[id]?.$el?.querySelector('[contenteditable]')?.focus();
    }
};

const commitTextEdit = ({ recalculateHeight = true, reason = 'commit-text-edit' } = {}) => {
    if (!editingElementId.value) return;

    const id = editingElementId.value;
    const editorRef = richEditorRefs.value[id];
    const isLinkedText = state.customElements?.[id]?.type === 'linkedText';

    if (editorRef?.getParagraphStyles && !isLinkedText) {
      onRichEditorStylesUpdate(id, editorRef.getParagraphStyles());
    }

    if (recalculateHeight) {
      recalculateTextHeight(id);
    } else if (id === 'title') {
      frontendLog.info('title-height', 'Se preserva altura de titulo al cerrar edicion', {
        id,
        reason,
        activePageId: activePageId.value,
        currentHeight: state.elementLayout?.[id]?.h ?? null,
      });
    }

    // Si es linkedText, detener edición en el sistema
    if (state.customElements?.[id]?.type === 'linkedText') {
      const layout = state.elementLayout[id];
      if (layout?.linkedTextGroupId) {
        linkedTextBoxSystem.stopEditing(layout.linkedTextGroupId);
      }
    }

    paragraphSelection.start = selectedParagraphIndex.value;
    paragraphSelection.end = selectedParagraphIndex.value;
    paragraphSelection.active = false;
    editingElementId.value = null;
    editingBoxHeight.value = null;
    activeLinkedTextBox.value = null;
};

const cancelTextEdit = () => {
    const id = editingElementId.value;
    if (state.customElements?.[id]?.type === 'linkedText') {
      const layout = state.elementLayout[id];
      if (layout?.linkedTextGroupId) {
        linkedTextBoxSystem.stopEditing(layout.linkedTextGroupId);
      }
    }
    editingElementId.value = null;
    editingBoxHeight.value = null;
    paragraphSelection.start = selectedParagraphIndex.value;
    paragraphSelection.end = selectedParagraphIndex.value;
    paragraphSelection.active = false;
    activeLinkedTextBox.value = null;
};


onMounted(() => {
  // Ya se hizo resetDesignerState y rehidratación arriba
  syncEditorViewport();
  editorViewportQuery = window.matchMedia('(max-width: 767px)');
  editorViewportQuery.addEventListener?.('change', syncEditorViewport);
  const nextSurface = currentCanvasDimensions();
  if (state.designSurface?.width && state.designSurface?.height) {
    rescaleDesignSurface(state.designSurface, nextSurface);
  } else {
    state.designSurface = nextSurface;
  }
  pushHistorySnapshot({ force: true });
  document.addEventListener('pointerdown', handleGlobalPointerDown, true);
  document.addEventListener('pointermove', handlePinchPointerMove, { passive: false });
  document.addEventListener('pointermove', moveDrag, { passive: false });
  document.addEventListener('pointermove', handleLinkedTextLinkMove, { passive: false });
  document.addEventListener('pointerup', handleDocumentPointerEnd);
  document.addEventListener('pointerup', handlePinchPointerEnd);
  document.addEventListener('pointercancel', handleDocumentPointerEnd);
  document.addEventListener('pointercancel', handlePinchPointerEnd);
  document.addEventListener('keydown', handleClipboardKeydown);
  document.addEventListener('keydown', handleGlobalKeydown);
  document.addEventListener('paste', handleDocumentPaste);
  document.addEventListener('dragover', handleCanvasFileDragOver);
  document.addEventListener('drop', handleCanvasFileDragLeave);
  syncUploadedAssetsLibrary();
  syncPendingUploadsFromPersistedState();
  loadAdminTemplates();
  if (shouldOpenTemplateForm && authUser.value?.name === 'admin') {
    resetTemplateForm(currentDesignTemplate.value);
    templateFormOpen.value = true;
  }
  refreshElementObservers();
  visuallyFocusedPageId.value = activePageId.value;
  nextTick(() => updateVisuallyFocusedPage());

  if (isTemplateBaseEditor.value) {
    scheduleThumbnailCapture();
    requestImmediateStateFlush();
  }
});


// --- SIEMPRE GENERAR MINIATURA ANTES DE GUARDAR ESTADO ---
// Debounce para evitar capturas excesivas
const flushDesignerStateWithThumbnail = async () => {
  if (pendingStateFlush) {
    stateFlushRequestedDuringPending = true;
    return;
  }
  pendingStateFlush = true;
  stateFlushRequestedDuringPending = false;
  syncActivePageSnapshot();
  generateThumbnailAndThen(async () => {
    try {
      syncActivePageSnapshot();
      await flushDesignerStatePersistence();
    } catch (error) {
      console.error('No se pudo guardar el estado del diseño automáticamente', error);
    } finally {
      pendingStateFlush = false;
      if (stateFlushRequestedDuringPending) {
        stateFlushRequestedDuringPending = false;
        flushDesignerStateWithThumbnail();
      }
    }
  });
};

// Watcher principal para cambios en el diseño
watch(
  () => [state.content, state.elementLayout, state.customElements],
  () => {
    if (isSwitchingDocumentPage) return;
    if (exportDialogOpen.value) {
      return;
    }
    scheduleHistorySnapshot();
    flushDesignerStateWithThumbnail();
  },
  { deep: true }
);

onBeforeUnmount(() => {
  editorViewportQuery?.removeEventListener?.('change', syncEditorViewport);
  editorViewportQuery = null;
  document.removeEventListener('pointerdown', handleGlobalPointerDown, true);
  document.removeEventListener('pointermove', handlePinchPointerMove);
  document.removeEventListener('pointermove', moveDrag);
  document.removeEventListener('pointerup', handleDocumentPointerEnd);
  document.removeEventListener('pointerup', handlePinchPointerEnd);
  document.removeEventListener('pointercancel', handleDocumentPointerEnd);
  document.removeEventListener('pointercancel', handlePinchPointerEnd);
  document.removeEventListener('keydown', handleClipboardKeydown);
  document.removeEventListener('keydown', handleGlobalKeydown);
  document.removeEventListener('paste', handleDocumentPaste);
  document.removeEventListener('dragover', handleCanvasFileDragOver);
  document.removeEventListener('drop', handleCanvasFileDragLeave);
  if (visiblePageFrame !== null) {
    cancelAnimationFrame(visiblePageFrame);
    visiblePageFrame = null;
  }
  if (thumbnailTimer) {
    clearTimeout(thumbnailTimer);
    thumbnailTimer = null;
  }
  elementObservers.forEach((observer) => observer.disconnect());
  elementObservers.clear();
  clearLongPress();
  setDragDocumentState(false);
  fileDragActive.value = false;
});

watch(editorElements, () => {
    Object.entries(groupedElements).forEach(([groupId, group]) => {
      group.elementIds = group.elementIds.filter((id) => Boolean(state.elementLayout[id]));
      if (group.elementIds.length < 2) {
        delete groupedElements[groupId];
        if (selectedGroupId.value === groupId) {
          selectedGroupId.value = null;
        }
      }
    });

    refreshElementObservers();
}, { deep: true });

watch(
  () => [state.content, state.elementLayout, state.customElements],
  async () => {
    // ...el guardado ahora lo hace flushDesignerStateWithThumbnail
  },
  { deep: true }
);

watch(
  () => {
    const linkedLayouts = {};
    Object.entries(state.elementLayout).forEach(([key, layout]) => {
      if (layout.linkedTextGroupId) {
        linkedLayouts[key] = {
          w: layout.w,
          h: layout.h,
          groupId: layout.linkedTextGroupId,
          fontSize: layout.fontSize,
          fontFamily: layout.fontFamily,
          fontWeight: layout.fontWeight,
          italic: layout.italic,
          underline: layout.underline,
          uppercase: layout.uppercase,
          textAlign: layout.textAlign,
          color: layout.color,
          letterSpacing: layout.letterSpacing,
          lineHeight: layout.lineHeight,
          paragraphStyles: layout.paragraphStyles,
        };
      }
    });
    return JSON.stringify(linkedLayouts);
  },
  () => {
    if (isSwitchingDocumentPage) {
      frontendLog.debug('linked-text-page-switch', 'Se omite redistribucion de linkedText durante cambio de pagina', {
        activePageId: activePageId.value,
      });
      return;
    }
    const handledGroups = new Set();
    Object.keys(state.elementLayout).forEach((key) => {
      const layout = state.elementLayout[key];
      if (layout?.linkedTextGroupId && !handledGroups.has(layout.linkedTextGroupId)) {
        handledGroups.add(layout.linkedTextGroupId);
        recalculateLinkedTextAllocations(getLinkedTextChainHead(key));
      }
    });
  }
);

const closeOptionsPanel = () => {
  optionsPanelOpen.value = false;
  activePropertyPanel.value = null;
  textPanelOpen.value = false;
  imagePanelOpen.value = false;
  shapePanelOpen.value = false;
};

const selectBackgroundWithoutOpeningPanel = () => {
  state.selectedElementId = 'background';
  closeOptionsPanel();
};

const endSelection = () => {
    state.selectedElementId = null;
    multiSelectionIds.value = [];
    selectedGroupId.value = null;
}

const openTextInsertPanel = () => {
  textPanelOpen.value = true;
  imagePanelOpen.value = false;
  shapePanelOpen.value = false;
  optionsPanelOpen.value = true;
};
const openImageInsertPanel = () => {
  imagePanelOpen.value = true;
  textPanelOpen.value = false;
  shapePanelOpen.value = false;
  optionsPanelOpen.value = true;
};
const openShapeInsertPanel = () => {
  shapePanelOpen.value = true;
  textPanelOpen.value = false;
  imagePanelOpen.value = false;
  optionsPanelOpen.value = true;
};
const openBackgroundPanel = () => {
  selectBackgroundWithoutOpeningPanel();
};
const setImageInputRef = (element) => {
  imageInputRef.value = element;
};
const setCanvasRef = (element) => {
  canvasRef.value = element;
};
const setRichEditorRef = (id, element) => {
  if (element) {
    richEditorRefs.value[id] = element;
    return;
  }
  delete richEditorRefs.value[id];
};

// Nuevo handler para abrir el modal de exportación
const handleExportNavigation = async (event) => {
  event?.preventDefault?.();
  // Si es invitado, mostrar alerta y no abrir el exportador
  if (!authUser.value) {
    window.alert('Para descargar o exportar tu diseño debes iniciar sesión. Puedes seguir editando como invitado.');
    return;
  }
  exportDialogOpen.value = true;
};

const handleHomeNavigation = async () => {
  router.visit('/')
};

const handleLogout = async () => {
  try {
    await axios.post('/auth/logout');
    router.visit('/');
  } catch (error) {
    console.error('Failed to logout from editor app', error);
  };
}

const handleLogin = async () => {
  router.visit('/auth/login?from_editor=1');
};

const handleCreateNewDesign = async () => {
  // Si es invitado y ya existe un diseño temporal, mostrar alerta y no crear otro
  if (!authUser.value && state.currentDesignUuid == null && window.sessionStorage.getItem('guestDesignCreated')) {
    window.alert('Solo puedes tener un diseño temporal como invitado. Inicia sesión para guardar y crear más diseños.');
    return;
  }
  try {
    await axios.delete(resetEndpoint.value);
  } catch (error) {
    console.error('Failed to reset current designer state', error);
  }

  resetDesignerState();
  // Marcar que el invitado ya creó un diseño temporal
  if (!authUser.value) {
    window.sessionStorage.setItem('guestDesignCreated', '1');
  }
  window.location.href = '/';
};

const handleDuplicateDesign = async () => {
  if (authUser.value && currentDesignDuplicateEndpoint.value) {
    try {
      const response = await axios.post(currentDesignDuplicateEndpoint.value);
      const duplicateUuid = response.data?.design?.uuid;

      if (duplicateUuid) {
        state.currentDesignUuid = duplicateUuid;
        window.location.href = `/designer/editor?design=${duplicateUuid}`;
        return;
      }
    } catch (error) {
      console.error('Failed to duplicate persisted design', error);
    }
  }

  const currentTitle = (state.designTitle || 'Diseño sin título').trim();
  state.designTitle = currentTitle.toLowerCase().startsWith('copia de ')
    ? currentTitle
    : `Copia de ${currentTitle}`;
  state.designTitleManual = true;

  try {
    await flushDesignerStatePersistence();
  } catch (error) {
    console.error('Failed to persist duplicated design title', error);
  }
};

const handleRenameDesign = async () => {
  const nextTitle = window.prompt('Nuevo título del diseño', state.designTitle || 'Diseño sin título');
  if (nextTitle === null) return;

  state.designTitle = nextTitle.trim() || 'Diseño sin título';
  state.designTitleManual = true;

  try {
    if (authUser.value && currentDesignRenameEndpoint.value) {
      await axios.patch(currentDesignRenameEndpoint.value, {
        name: state.designTitle,
      });
      return;
    }

    await flushDesignerStatePersistence();
  } catch (error) {
    console.error('Failed to persist design title rename', error);
  }
};

const ensurePersistedDesign = async () => {
  if (!authUser.value) {
    throw new Error('Debes iniciar sesión para guardar este diseño.');
  }

  if (state.currentDesignUuid) {
    await flushDesignerStatePersistence();
    return state.currentDesignUuid;
  }

  if (!designsStoreEndpoint.value) {
    throw new Error('No hay endpoint disponible para crear diseños.');
  }

  const response = await axios.post(designsStoreEndpoint.value, {
    state: JSON.parse(JSON.stringify(state)),
    name: state.designTitle || 'Diseño sin título',
  });
  const uuid = response.data?.design?.uuid;
  if (!uuid) {
    throw new Error('No se pudo persistir el diseño actual.');
  }

  state.currentDesignUuid = uuid;
  return uuid;
};

const splitPromptList = (value) => String(value || '')
  .split(',')
  .map((item) => item.trim())
  .filter(Boolean);

const parseFieldMappingsText = (value) => {
  const source = String(value || '').trim();
  if (!source) return [];

  try {
    const decoded = JSON.parse(source);
    return Array.isArray(decoded) ? decoded : [];
  } catch {
    return source
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const [left, propertyCandidate] = line.split(':').map((part) => part.trim());
        const [sourceField, target] = left.split('->').map((part) => part.trim());
        if (!sourceField || !target) return null;

        if (target.startsWith('#')) {
          return {
            sourceField,
            elementId: target.slice(1),
            property: propertyCandidate === 'src' ? 'src' : 'text',
          };
        }

        return {
          sourceField,
          targetField: target,
        };
      })
      .filter(Boolean);
  }
};

const stringifyFieldMappings = (mappings = []) => (Array.isArray(mappings) ? mappings : [])
  .map((mapping) => {
    if (mapping.elementId) {
      return `${mapping.sourceField} -> #${mapping.elementId}${mapping.property ? `:${mapping.property}` : ''}`;
    }

    return `${mapping.sourceField} -> ${mapping.targetField || ''}`;
  })
  .join('\n');

const normalizeMappingRows = (mappings = []) => {
  const rows = Array.isArray(mappings) ? mappings : [];
  return rows.length
    ? rows.map((mapping) => ({
      sourceField: mapping?.sourceField ?? mapping?.fieldName ?? '',
      mode: mapping?.elementId ? 'element' : 'field',
      targetField: mapping?.targetField ?? '',
      elementId: mapping?.elementId ?? '',
      property: mapping?.property ?? 'text',
      label: mapping?.label ?? '',
      fallback: mapping?.fallback ?? '',
    }))
    : [{
      sourceField: '',
      mode: 'field',
      targetField: '',
      elementId: '',
      property: 'text',
      label: '',
      fallback: '',
    }];
};

const serializeMappingRows = (rows = []) => rows
  .map((row) => ({
    sourceField: String(row.sourceField ?? '').trim(),
    targetField: row.mode === 'field' ? String(row.targetField ?? '').trim() : '',
    elementId: row.mode === 'element' ? String(row.elementId ?? '').trim() : '',
    property: row.mode === 'element' ? (row.property === 'src' ? 'src' : 'text') : undefined,
    label: String(row.label ?? '').trim(),
    fallback: String(row.fallback ?? '').trim(),
  }))
  .filter((row) => row.sourceField && (row.targetField || row.elementId))
  .map((row) => Object.fromEntries(Object.entries(row).filter(([, value]) => value !== '' && value !== undefined)));

const toggleArrayValue = (arrayRef, value) => {
  const index = arrayRef.indexOf(value);
  if (index >= 0) {
    arrayRef.splice(index, 1);
  } else {
    arrayRef.push(value);
  }
};

const removeArrayValue = (arrayRef, value) => {
  const index = arrayRef.indexOf(value);
  if (index >= 0) arrayRef.splice(index, 1);
};

const addMappingRow = () => {
  templateForm.fieldMappings.push({
    sourceField: '',
    mode: 'field',
    targetField: '',
    elementId: '',
    property: 'text',
    label: '',
    fallback: '',
  });
};

const removeMappingRow = (index) => {
  templateForm.fieldMappings.splice(index, 1);
  if (!templateForm.fieldMappings.length) addMappingRow();
};

const loadAdminTemplates = async () => {
  if (authUser.value?.name !== 'admin') return;

  try {
    const response = await axios.get('/designer/design-templates', {
      params: { includeDrafts: 1 },
    });
    adminTemplates.value = response.data?.templates ?? [];
  } catch (error) {
    console.error('No se pudieron cargar las plantillas para admin', error);
  }
};

const resetTemplateForm = (template = null) => {
  templateForm.uuid = template?.uuid ?? template?.id ?? null;
  templateForm.title = template?.title ?? state.designTitle ?? 'Nueva plantilla';
  templateForm.description = template?.description ?? '';
  templateForm.categoryIds = [...(template?.category_ids ?? (state.templateCategory && state.templateCategory !== 'all' ? [state.templateCategory] : ['general']))];
  templateForm.objectiveIds = [...(template?.objective_ids ?? (state.objective ? [state.objective] : ['generic']))];
  templateForm.fieldMappings = normalizeMappingRows(template?.field_mappings ?? []);
  templateForm.status = template?.status ?? 'published';
  templateForm.featured = Boolean(template?.featured ?? false);
  templateForm.sortOrder = Number(template?.sort_order ?? 0);
};

const handlePublishDesignTemplate = async () => {
  if (authUser.value?.name !== 'admin') return;

  await loadAdminTemplates();
  resetTemplateForm(currentDesignTemplate.value);
  templateFormOpen.value = true;
};

const handleTemplateSettingsOpen = async () => {
  if (authUser.value?.name !== 'admin') return;

  await loadAdminTemplates();
  resetTemplateForm(currentDesignTemplate.value);
  templateFormOpen.value = true;
};

const closeTemplateForm = () => {
  if (templateFormSaving.value) return;
  templateFormOpen.value = false;
};

const saveTemplateForm = async () => {
  if (authUser.value?.name !== 'admin' || templateFormSaving.value) return;

  const categories = templateForm.categoryIds.map((item) => String(item).trim()).filter(Boolean);
  const objectives = templateForm.objectiveIds.map((item) => String(item).trim()).filter(Boolean);
  if (!templateForm.title.trim() || !categories.length || !objectives.length) {
    window.alert('La plantilla necesita título, al menos una categoría y al menos un objetivo.');
    return;
  }

  templateFormSaving.value = true;
  try {
    const payload = {
      title: templateForm.title.trim(),
      description: templateForm.description.trim(),
      category_ids: categories,
      objective_ids: objectives,
      field_mappings: serializeMappingRows(templateForm.fieldMappings),
      status: templateForm.status,
      featured: Boolean(templateForm.featured),
      sort_order: Number(templateForm.sortOrder) || 0,
    };
    const response = templateForm.uuid
      ? await axios.patch(`/designer/design-templates/${templateForm.uuid}`, payload)
      : await axios.post(`/designer/designs/${await ensurePersistedDesign()}/template`, payload);
    const savedTemplate = response.data?.template;

    if (savedTemplate) {
      state.selectedTemplateId = savedTemplate.uuid ?? savedTemplate.id;
      const existingIndex = adminTemplates.value.findIndex((template) => template.uuid === savedTemplate.uuid);
      if (existingIndex >= 0) {
        adminTemplates.value.splice(existingIndex, 1, savedTemplate);
      } else {
        adminTemplates.value.unshift(savedTemplate);
      }
      resetTemplateForm(savedTemplate);
    }

    templateFormOpen.value = false;
  } catch (error) {
    console.error('Failed to save design template', error);
    window.alert(error.response?.data?.message || error.message || 'No se pudo guardar la plantilla.');
  } finally {
    templateFormSaving.value = false;
  }
};

const handleAssistantFinish = async ({ selectedTemplate, designerState } = {}) => {
  const assistantState = designerState
    ? JSON.parse(JSON.stringify(designerState))
    : JSON.parse(JSON.stringify(state));
  const persistedTemplate = selectedTemplate?.uuid
    ? selectedTemplate
    : persistedTemplates.value.find((template) => template.id === assistantState.selectedTemplateId || template.uuid === assistantState.selectedTemplateId);

  if (!persistedTemplate?.uuid) {
    normalizeBrochurePages(assistantState);
    assistantState.currentDesignUuid = currentDesignUuid.value;
    assistantState.stateRevision = bumpRevision(state.stateRevision);
    assistantState.templateRevision = state.templateRevision;
    useDesignerState({ forceRehydrate: true, overrideState: assistantState });
    ensureDocumentPages(true);
    refreshDocumentPageList();
    closeAssistant();
    return;
  }

  try {
    try {
      commitTextEdit();
    } catch (_) {
      // no-op: si el editor rico todavía no está listo, continuamos igualmente
    }
    const targetSurface = canvasDimensionsForDesignerState(assistantState);
    assistantState.stateRevision = bumpRevision(state.stateRevision);
    assistantState.templateRevision = bumpRevision(state.templateRevision);
    const response = await axios.post(`/designer/design-templates/${persistedTemplate.uuid}/generate`, {
      designerState: assistantState,
      content: JSON.parse(JSON.stringify(assistantState.content ?? {})),
      stateRevision: assistantState.stateRevision,
      templateRevision: assistantState.templateRevision,
      objective: assistantState.objective,
      outputType: assistantState.outputType,
      format: assistantState.format,
      size: assistantState.size,
      designTitle: assistantState.designTitle,
      designSurface: targetSurface,
      targetDesignUuid: isTemplateBaseEditor.value ? null : currentDesignUuid.value,
    });
    const uuid = response.data?.design?.uuid;
    const returnedState = response.data?.design?.state ?? null;
    if (returnedState) {
      normalizeBrochurePages(returnedState);
      // Forzar rehidratación del estado del diseñador con el state devuelto por el backend
      useDesignerState({ forceRehydrate: true, overrideState: returnedState });
      ensureDocumentPages(true);
      refreshDocumentPageList();
      state.currentDesignUuid = uuid;
      closeAssistant();
      return;
    }
    if (uuid) {
      state.currentDesignUuid = uuid;
      window.location.href = `/designer/editor?design=${uuid}`;
      return;
    }
  } catch (error) {
    window.alert(error.response?.data?.message || 'No se pudo generar el diseño desde la plantilla.');
  }

  closeAssistant();
};

const handleCanvasClick = (event) => {
  if (Date.now() < suppressCanvasClickUntil.value) return;
  if (event.target.closest('[data-editor-element="true"]') || event.target.closest('[data-editor-control="true"]')) return;
  selectBackgroundWithoutOpeningPanel();
};

const ensurePageInteractionContext = (pageId) => {
  if (!pageId) return;
  if (pageId === workingDocumentPageId.value) {
    if (pageId !== activePageId.value) {
      setVisualActiveDocumentPage(pageId);
    }
    return;
  }
  void switchToPage(pageId);
};

const handlePageCanvasPointerDownWithPinch = (pageId, event) => {
  ensurePageInteractionContext(pageId);
  handleCanvasPointerDownWithPinch(event);
};

const handlePageCanvasClick = (pageId, event) => {
  ensurePageInteractionContext(pageId);
  handleCanvasClick(event);
};

const handlePageElementPointerDown = (pageId, event, id) => {
  ensurePageInteractionContext(pageId);
  handleElementPointerDown(event, id);
  linkedTextOverlayRevision.value += 1;
};

const handlePageElementClick = (pageId, event, id) => {
  ensurePageInteractionContext(pageId);
  handleElementClick(event, id);
  linkedTextOverlayRevision.value += 1;
};

const beginPageTextEdit = (pageId, id, focusToEnd = false, event = null) => {
  ensurePageInteractionContext(pageId);
  beginTextEdit(id, focusToEnd, event);
};

const normalizeDesignTitleCandidate = (value) => String(value ?? '')
  .trim()
  .replace(/\s+/g, ' ')
  .toLowerCase();

const isPlaceholderDesignTitle = (value) => {
  const normalized = normalizeDesignTitleCandidate(value);
  return !normalized || [
    'titulo',
    'título',
    'agrega un titulo',
    'agrega un título',
    'diseno sin titulo',
    'diseño sin título',
  ].includes(normalized);
};

watch(() => state.selectedElementId, () => {
    toolbarPosition.x = 0;
    toolbarPosition.y = 3;
  linkedTextOverlayRevision.value += 1;
  if (state.selectedElementId) {
    selectedGroupId.value = null;
    multiSelectionIds.value = [];
  }
});

watch(selectedGroupId, (groupId) => {
  if (!groupId) return;
  state.selectedElementId = null;
  activePropertyPanel.value = null;
});

watch(
  () => state.content.title,
  (nextTitle) => {
    if (state.designTitleManual) return;
    if (isPlaceholderDesignTitle(nextTitle)) return;

    state.designTitle = String(nextTitle).trim();
  },
  { immediate: true }
);

</script>

<template>
  <DesignerLayout
    title="Editor simplificado"
    eyebrow="Pantalla 6"
    description="Selecciona un texto para editarlo."
    :current-step="currentStep"
    :steps="steps"
    :show-steps="false"
    :show-header="false"
    :full-height="true"
  >
    <div class="flex h-full min-h-0 flex-col overflow-hidden bg-base-100">

    <EditorTopBar
      :auth-user="authUser"
      :design-title="state.designTitle"
      :size="state.size"
      :can-undo="canUndo"
      :can-redo="canRedo"
      :undo-action-label="undoActionLabel"
      :redo-action-label="redoActionLabel"
      :zoom-level="zoomLevel"
      :template-mode="isTemplateBaseEditor"
      @go-home="handleHomeNavigation"
      @create-new-design="handleCreateNewDesign"
      @download-design="handleExportNavigation"
      @duplicate-design="handleDuplicateDesign"
      @login="handleLogin"
      @logout="handleLogout"
      @rename-design="handleRenameDesign"
      @publish-design-template="handlePublishDesignTemplate"
      @open-design-assistant-step="openAssistantStep"
      @undo="performUndo"
      @redo="performRedo"
      @update-zoom-level="setZoomLevel"
      @export-navigate="handleExportNavigation"

      />
    <ExportDialog v-if="exportDialogOpen" :navigation="navigation" @close="exportDialogOpen = false" />

    <TemplateFormModal
      :open="templateFormOpen"
      :saving="templateFormSaving"
      :eyebrow="templateForm.uuid ? 'Editar plantilla' : 'Publicar plantilla'"
      title="Datos de la plantilla"
      description="Solo el usuario admin puede publicar y modificar plantillas."
      :submit-label="templateForm.uuid ? 'Guardar cambios' : 'Publicar plantilla'"
      @close="closeTemplateForm"
      @submit="saveTemplateForm"
    >
      <div class="grid gap-4 sm:grid-cols-2">
        <label class="sm:col-span-2">
          <span class="text-sm font-medium">T??tulo</span>
          <input v-model="templateForm.title" required maxlength="255" class="input input-bordered mt-2 w-full" />
        </label>

        <label class="sm:col-span-2">
          <span class="text-sm font-medium">Descripci??n</span>
          <textarea v-model="templateForm.description" maxlength="2000" class="textarea textarea-bordered mt-2 min-h-24 w-full"></textarea>
        </label>

        <div class="sm:col-span-2 grid gap-4 lg:grid-cols-2">
          <section class="rounded-[24px] border border-base-300 bg-base-100 p-4">
            <div class="flex items-center justify-between gap-3">
              <div>
                <p class="text-sm font-semibold">Categor??as</p>
                <p class="text-xs text-base-content/60">Puedes seleccionar varias.</p>
              </div>
              <span class="badge badge-primary badge-outline">{{ templateForm.categoryIds.length }}</span>
            </div>

            <div v-if="templateForm.categoryIds.length" class="mt-3 flex flex-wrap gap-2">
              <button
                v-for="category in templateForm.categoryIds"
                :key="`selected-category-${category}`"
                type="button"
                class="badge badge-primary gap-2 py-3"
                @click="removeArrayValue(templateForm.categoryIds, category)"
              >
                {{ filterLabels[category] || category }} ??
                </button>
              </div>

            <div class="dropdown dropdown-bottom mt-3 w-full">
              <button type="button" tabindex="0" class="btn btn-outline w-full justify-between rounded-2xl">
                Elegir categor??as
                <span>???</span>
              </button>
              <div tabindex="0" class="dropdown-content z-[100] mt-2 max-h-80 w-full overflow-y-auto rounded-2xl border border-base-300 bg-base-100 p-2 shadow-xl">
                <button
                  v-for="option in templateCategoryOptions"
                  :key="option.id"
                  type="button"
                  class="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left hover:bg-base-200"
                  @click="toggleArrayValue(templateForm.categoryIds, option.id)"
                >
                  <input type="checkbox" class="checkbox checkbox-primary checkbox-sm" :checked="templateForm.categoryIds.includes(option.id)" readonly />
                  <span class="font-medium">{{ option.label }}</span>
                </button>
              </div>
            </div>
          </section>

          <section class="rounded-[24px] border border-base-300 bg-base-100 p-4">
            <div class="flex items-center justify-between gap-3">
              <div>
                <p class="text-sm font-semibold">Objetivos compatibles</p>
                <p class="text-xs text-base-content/60">???Gen??rico??? aparece en cualquier objetivo.</p>
              </div>
              <span class="badge badge-primary badge-outline">{{ templateForm.objectiveIds.length }}</span>
            </div>

            <div v-if="templateForm.objectiveIds.length" class="mt-3 flex flex-wrap gap-2">
              <button
                v-for="objective in templateForm.objectiveIds"
                :key="`selected-objective-${objective}`"
                type="button"
                class="badge badge-secondary gap-2 py-3"
                @click="removeArrayValue(templateForm.objectiveIds, objective)"
              >
                {{ templateObjectiveOptions.find((item) => item.id === objective)?.title || objective }} ??
              </button>
            </div>

            <div class="dropdown dropdown-bottom mt-3 w-full">
              <button type="button" tabindex="0" class="btn btn-outline w-full justify-between rounded-2xl">
                Elegir objetivos
                <span>???</span>
              </button>
              <div tabindex="0" class="dropdown-content z-[100] mt-2 max-h-80 w-full overflow-y-auto rounded-2xl border border-base-300 bg-base-100 p-2 shadow-xl">
                <button
                  v-for="option in templateObjectiveOptions"
                  :key="option.id"
                  type="button"
                  class="flex w-full items-start gap-3 rounded-xl px-3 py-2 text-left hover:bg-base-200"
                  @click="toggleArrayValue(templateForm.objectiveIds, option.id)"
                >
                  <input type="checkbox" class="checkbox checkbox-primary checkbox-sm mt-1" :checked="templateForm.objectiveIds.includes(option.id)" readonly />
                  <span>
                    <span class="block font-medium">{{ option.title }}</span>
                    <span class="block text-xs text-base-content/60">{{ option.description }}</span>
                  </span>
                </button>
              </div>
            </div>
          </section>
        </div>

        <label>
          <span class="text-sm font-medium">Estado</span>
          <select v-model="templateForm.status" class="select select-bordered mt-2 w-full">
            <option value="draft">Borrador</option>
            <option value="published">Publicada</option>
            <option value="archived">Archivada</option>
          </select>
        </label>

        <label>
          <span class="text-sm font-medium">Orden</span>
          <input v-model.number="templateForm.sortOrder" min="0" type="number" class="input input-bordered mt-2 w-full" />
        </label>

        <label class="flex items-center gap-3 rounded-2xl border border-base-300 bg-base-100 p-4">
          <input v-model="templateForm.featured" type="checkbox" class="checkbox checkbox-primary" />
          <span>
            <span class="block text-sm font-medium">Destacada</span>
            <span class="block text-xs text-base-content/60">Aparecer?? antes en el asistente.</span>
          </span>
        </label>

        <section class="sm:col-span-2 rounded-[24px] border border-base-300 bg-base-100 p-4">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p class="text-sm font-semibold">Mapeos de campos</p>
              <p class="text-xs text-base-content/60">
                ??salos para reinterpretar datos: por ejemplo, <code>datos1</code> como contacto.
              </p>
            </div>
            <button type="button" class="btn btn-outline btn-sm rounded-full" @click="addMappingRow">
              + A??adir mapeo
            </button>
          </div>

          <div class="mt-4 space-y-3">
            <article
              v-for="(mapping, index) in templateForm.fieldMappings"
              :key="`mapping-${index}`"
              class="grid gap-3 rounded-2xl border border-base-300 bg-base-200/40 p-3 lg:grid-cols-[1fr,140px,1fr,110px,auto]"
            >
              <label>
                <span class="text-xs font-semibold uppercase tracking-[0.16em] text-base-content/60">Campo origen</span>
                <input v-model="mapping.sourceField" class="input input-bordered input-sm mt-1 w-full" placeholder="datos1" />
              </label>

              <label>
                <span class="text-xs font-semibold uppercase tracking-[0.16em] text-base-content/60">Destino</span>
                <select v-model="mapping.mode" class="select select-bordered select-sm mt-1 w-full">
                  <option value="field">Campo</option>
                  <option value="element">Elemento</option>
                </select>
              </label>

              <label v-if="mapping.mode === 'field'">
                <span class="text-xs font-semibold uppercase tracking-[0.16em] text-base-content/60">Campo destino</span>
                <input v-model="mapping.targetField" class="input input-bordered input-sm mt-1 w-full" placeholder="contact" />
              </label>
              <label v-else>
                <span class="text-xs font-semibold uppercase tracking-[0.16em] text-base-content/60">ID elemento</span>
                <input v-model="mapping.elementId" class="input input-bordered input-sm mt-1 w-full" placeholder="footer-contact" />
              </label>

              <label>
                <span class="text-xs font-semibold uppercase tracking-[0.16em] text-base-content/60">Propiedad</span>
                <select v-model="mapping.property" class="select select-bordered select-sm mt-1 w-full" :disabled="mapping.mode === 'field'">
                  <option value="text">Texto</option>
                  <option value="src">Imagen</option>
                </select>
              </label>

              <button type="button" class="btn btn-ghost btn-sm self-end rounded-full text-error" @click="removeMappingRow(index)">
                Quitar
              </button>
            </article>
          </div>
        </section>
      </div>
    </TemplateFormModal>


    <section class="relative min-h-0 flex-1 overflow-hidden">
      <div class="h-full overflow-hidden border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
          <EditorFloatingToolbar
            v-if="hasSelection && !hasMultiSelection && !isGroupSelection"
          :active-element-label="activeElementLabel"
          :active-property-panel="activePropertyPanel"
          :current-alignment-icon="currentAlignmentIcon"
          :has-text-selection="hasTextSelection"
            :selected-property-tabs="selectedPropertyTabs"
            :selected-text-style="selectedTextStyle"
            :toolbar-position="toolbarPosition"
            :mobile-mode="isMobileEditor"
          @cycle-alignment="cycleAlignment"
          @property-tab-click="handlePropertyTabClick"
          @start-drag="startToolbarDrag"
          @close-bar="endSelection"
        />

        <div class="relative grid h-full min-h-0 gap-0" :style="editorGridStyle">
          <!-- Panel de CreaciÃƒÂ³n (vertical, siempre visible) -->
          <EditorInsertSidebar
            class="fixed inset-x-0 bottom-0 z-[60] md:static md:z-auto"
            :class="hasSelection && !hasMultiSelection && !isGroupSelection ? 'max-md:hidden' : ''"
            :text-panel-open="textPanelOpen"
            :image-panel-open="imagePanelOpen"
            :shape-panel-open="shapePanelOpen"
            :is-background-selected="state.selectedElementId === 'background'"
            @open-text-panel="openTextInsertPanel"
            @open-image-panel="openImageInsertPanel"
            @open-shape-panel="openShapeInsertPanel"
            @select-background-panel="openBackgroundPanel"
            @add-linked-text="addLinkedTextElement"
          />

          <!-- Panel de Opciones (condicionalmente visible) -->
          <EditorContextPanel
            v-if="isOptionsPanelVisible"
            :state="state"
            :has-selection="hasSelection"
            :has-text-selection="hasTextSelection"
            :active-property-panel="activePropertyPanel"
            :active-property-title="activePropertyTitle"
            :template-mode="isTemplateBaseEditor"
            :template-fields="templateFieldDefinitions"
            :template-field-usage="Object.fromEntries(templateFieldDefinitions.map((field) => [field.id, Boolean(state.elementLayout?.[field.id])]))"
            :on-add-template-field="addTemplateFieldElement"
            :on-remove-template-field="removeTemplateFieldElement"
            :text-panel-open="textPanelOpen"
            :image-panel-open="imagePanelOpen"
            :shape-panel-open="shapePanelOpen"
            :text-presets="textPresets"
            :image-panel-tabs="imagePanelTabs"
            :image-panel-tab="imagePanelTab"
            :image-url-input="imageUrlInput"
            :image-library="imageLibrary"
            :shape-category-filter="shapeCategoryFilter"
            :shape-categories="shapeCategories"
            :shape-style-from-kind="shapeStyleFromKind"
            :selected-element="selectedElement"
            :selected-element-type="selectedElementType"
            :background-has-image="backgroundHasImage"
            :selected-text-style="selectedTextStyle"
            :active-paragraph-label="activeParagraphLabel"
            :font-options="fontOptions"
            :color-options="colorOptions"
            :background-options="backgroundOptions"
            :design-color-options="designColorOptions"
            :design-gradient-options="designGradientOptions"
            :text-effect-rows="textEffectRows"
            :visual-effect-rows="visualEffectRows"
            :active-text-effect-id="activeTextEffectId"
            :active-visual-effect-id="activeVisualEffectId"
            :text-effect-card-font-family="textEffectCardFontFamily"
            :text-effect-preview-style="textEffectPreviewStyle"
            :visual-effect-preview-style="visualEffectPreviewStyle"
            :shape-gradient-options="shapeGradientOptions"
            :shape-gradient-directions="shapeGradientDirections"
            :normalize-picker-color="normalizePickerColor"
            :image-input-ref-setter="setImageInputRef"
            :add-text-element="addTextElement"
            :add-linked-text-element="addLinkedTextElement"
            :trigger-image-picker="triggerImagePicker"
            :on-image-picked="onImagePicked"
            :add-image-from-url="addImageFromUrl"
            :add-library-image="addLibraryImage"
            :add-uploaded-image="addUploadedImage"
            :get-upload-progress="getUploadProgress"
            :retry-uploaded-image="retryUploadedImage"
            :add-shape-element="addShapeElement"
            :apply-gradient-preset="applyGradientPreset"
            :apply-shape-gradient-preset="applyShapeGradientPreset"
            :swap-gradient-stops="swapGradientStops"
            :swap-shape-gradient-stops="swapShapeGradientStops"
            :set-text-effect="setTextEffect"
            :set-visual-effect="setVisualEffect"
            :activate-border-style="activateBorderStyle"
            :set-selected-color="setSelectedColor"
            :change-layer="changeLayer"
            :toggle-selected-image-flip="toggleSelectedImageFlip"
            :reset-selected-image-crop="resetSelectedImageCrop"
            @close-panel="closeOptionsPanel"
            @update-image-panel-tab="imagePanelTab = $event"
            @update-image-url-input="imageUrlInput = $event"
            @update-shape-category-filter="shapeCategoryFilter = $event"
          />

          <TemplateAdjustmentsPanel
            v-if="isTemplateBaseEditor"
            :template-fields="templateFieldDefinitions"
            :template-field-usage="templateFieldUsage"
            @add-field="addTemplateFieldElement"
            @hover-change="templatePanelHover = $event"
            @open-settings="handleTemplateSettingsOpen"
          />

          <div
            ref="canvasGridRef"
            class="canvas-grid relative h-full overflow-auto bg-slate-100 px-4 pt-6 pb-28 [touch-action:pan-x_pan-y] dark:bg-slate-950 sm:px-10 sm:pt-4 sm:pb-10 md:px-10 md:pt-16 md:pb-10"
            :style="canvasGridStyle"
            @scroll.passive="handleDocumentPagesScroll"
            @wheel.capture="handleCanvasWheel"
            @pointerdown="handleCanvasPointerDownWithPinch"
          >
            <svg
              v-if="linkedTextGlobalLinkLines.length"
              class="pointer-events-none absolute top-0 left-0 z-[300] overflow-visible text-emerald-400"
              :style="linkedTextOverlayStyle"
            >
              <line
                v-for="(line, idx) in linkedTextGlobalLinkLines"
                :key="`linked-text-global-line-${idx}`"
                :x1="line.x1"
                :y1="line.y1"
                :x2="line.x2"
                :y2="line.y2"
                stroke="currentColor"
                stroke-width="2"
                stroke-dasharray="5,5"
              />
            </svg>
            <div class="mx-auto flex w-full flex-col items-center gap-8">
              <section
                v-for="(documentPage, pageIndex) in documentPages"
                :key="documentPage.id"
                :ref="(element) => setDocumentPageRef(documentPage.id, element)"
                class="relative w-full max-w-full"
                :style="pageViewportStyle"
              >
                <div
                  class="absolute top-0 left-1/2 origin-top rounded-[28px] transition-shadow"
                  :class="[
                    drag.active && documentPage.id === workingDocumentPageId
                      ? 'z-[220]'
                      : (documentPage.id === workingDocumentPageId && (activeSelectionIds.length || selectionMarquee.active || multiSelectionIds.length > 1)
                          ? 'z-[180]'
                          : 'z-10'),
                    'shadow',
                  ]"
                  :style="pageChromeStyle"
                >
                <div class="relative z-50 mb-3 flex w-full items-center justify-between text-sm font-semibold text-slate-500 dark:text-slate-300" @pointerdown.stop>
                  <span>{{ hasMultiplePages ? physicalPageLabel(pageIndex) : '' }}</span>
                  <div class="relative z-50 flex items-center gap-1">
                    <span v-if="hasMultiplePages" class="tooltip tooltip-bottom order-first" data-tip="Mover página hacia arriba">
                      <button
                        type="button"
                        class="btn btn-ghost btn-xs"
                        :class="{ 'btn-disabled opacity-40': pageIndex === 0 }"
                        :disabled="pageIndex === 0"
                        aria-label="Mover página hacia arriba"
                        @click.stop.prevent="moveDocumentPage(documentPage.id, -1)"
                      >
                        <Icon icon="ph:arrow-up" class="h-4 w-4" />
                      </button>
                    </span>
                    <span v-if="hasMultiplePages" class="tooltip tooltip-bottom order-first" data-tip="Mover página hacia abajo">
                      <button
                        type="button"
                        class="btn btn-ghost btn-xs"
                        :class="{ 'btn-disabled opacity-40': pageIndex === documentPages.length - 1 }"
                        :disabled="pageIndex === documentPages.length - 1"
                        aria-label="Mover página hacia abajo"
                        @click.stop.prevent="moveDocumentPage(documentPage.id, 1)"
                      >
                        <Icon icon="ph:arrow-down" class="h-4 w-4" />
                      </button>
                    </span>
                    <span class="tooltip tooltip-bottom" data-tip="Duplicar página">
                      <button type="button" class="btn btn-ghost btn-xs" aria-label="Duplicar página" @click.stop.prevent="duplicateDocumentPage(documentPage.id)">
                        <Icon icon="ph:copy-simple" class="h-4 w-4" />
                      </button>
                    </span>
                    <span class="tooltip tooltip-bottom" data-tip="Nueva página">
                      <button type="button" class="btn btn-ghost btn-xs" aria-label="Nueva página" @click.stop.prevent="addDocumentPage({ afterPageId: documentPage.id })">
                        <Icon icon="ph:file-plus" class="h-4 w-4" />
                      </button>
                    </span>
                    <span
                      v-if="canDeleteDocumentPage"
                      class="tooltip tooltip-bottom"
                      :data-tip="deletePageTip"
                    >
                      <button
                        type="button"
                        class="btn btn-ghost btn-xs text-error"
                        aria-label="Eliminar página"
                        @click.stop.prevent="deleteDocumentPage(documentPage.id)"
                      >
                        <Icon icon="ph:trash" class="h-4 w-4" />
                      </button>
                    </span>
                  </div>
                </div>

                <div
                  class="relative z-[80] mx-auto overflow-visible"
                  :class="documentPage.id === activePageId ? 'outline outline-4 outline-primary/80 outline-offset-4 shadow-[0_0_0_8px_rgba(14,165,233,0.16)]' : ''"
                  :style="canvasFrameContainerStyle"
                >
                  <EditorCanvasStage
                    class="absolute inset-0 z-20"
                    :canvas-grid-style="{ minHeight: 'auto', padding: 0, background: 'transparent', overflow: 'visible', height: 'auto' }"
                    :canvas-frame-style="canvasFrameStyle"
                    :canvas-zoom-style="{}"
                    :is-background-selected="documentPage.id === workingDocumentPageId && state.selectedElementId === 'background'"
                    :canvas-background-style="pageCanvasBackgroundStyle(documentPage)"
                    :canvas-background-image-src="pageCanvasBackgroundImageSrc(documentPage)"
                    :canvas-background-image-style="pageCanvasBackgroundImageStyle(documentPage)"
                    :template-mode="isTemplateBaseEditor"
                    template-watermark="PLANTILLA"
                    :show-field-labels="templatePanelHover"
                    :canvas-element-style="canvasElementStyle"
                    :editor-elements="editorElementsForPage(documentPage)"
                    :drag="drag"
                    :file-drag-active="documentPage.id === activePageId && fileDragActive"
                    :background-drop-preview="documentPage.id === activePageId && backgroundDropPreview"
                    :active-page="documentPage.id === activePageId"
                    :active-page-id="activePageId"
                    :editing-element-id="documentPage.id === workingDocumentPageId ? editingElementId : null"
                    :state="stageStateForPage(documentPage)"
                    :element-box-style="(id) => pageElementBoxStyle(documentPage, id)"
                    :is-element-selected="(id) => documentPage.id === workingDocumentPageId && isElementSelected(id)"
                    :element-content-style="(id) => pageElementContentStyle(documentPage, id)"
                    :rich-editor-container-style="(id) => pageRichEditorContainerStyle(documentPage, id)"
                    :neon-color-override="(id) => pageNeonColorOverride(documentPage, id)"
                    :image-frame-style="(id) => pageImageFrameStyle(documentPage, id)"
                    :image-render-style="(id) => pageImageRenderStyle(documentPage, id)"
                    :image-tint-overlay-style="(id) => pageImageTintOverlayStyle(documentPage, id)"
                    :shape-style="(item) => pageShapeStyle(documentPage, item)"
                    :shape-render-model="(item) => pageShapeRenderModel(documentPage, item)"
                    :canvas-ref-setter="documentPage.id === activePageId ? setCanvasRef : null"
                    :rich-editor-ref-setter="documentPage.id === workingDocumentPageId ? setRichEditorRef : null"
                    :linked-text-link="linkedTextLink"
                    :active-linked-text-box="activeLinkedTextBox"
                    :hovered-field-key="hoveredFieldKey"
                    @canvas-pointer-down="handlePageCanvasPointerDownWithPinch(documentPage.id, $event)"
                    @canvas-click="handlePageCanvasClick(documentPage.id, $event)"
                    @field-hover="hoveredFieldKey = $event"
                    @canvas-file-drag-enter="handleCanvasFileDragEnter"
                    @canvas-file-drag-over="handleCanvasFileDragOver"
                    @canvas-file-drag-leave="handleCanvasFileDragLeave"
                    @canvas-file-drop="handleCanvasFileDrop"
                    @element-click="handlePageElementClick(documentPage.id, $event.event, $event.id)"
                    @begin-text-edit="beginPageTextEdit(documentPage.id, $event)"
                    @element-pointer-down="handlePageElementPointerDown(documentPage.id, $event.event, $event.id)"
                    @rich-editor-text-update="onRichEditorTextUpdate($event.id, $event.value)"
                    @rich-editor-styles-update="onRichEditorStylesUpdate($event.id, $event.value)"
                    @rich-editor-html-update="onRichEditorHtmlUpdate($event.id, $event.value)"
                    @rich-editor-selection-change="onRichEditorSelectionChange($event.id, $event.value)"
                    @rich-editor-blur="onRichEditorBlur($event.id, $event.event)"
                    @cancel-text-edit="cancelTextEdit"
                    @commit-text-edit="commitTextEdit"
                    @linked-text-link-start="handleLinkedTextLinkStart"
                  >
                    <template #overlay>
                      <SelectionOverlay
                        v-if="documentPage.id === workingDocumentPageId && (activeSelectionIds.length || selectionMarquee.active || multiSelectionIds.length > 1)"
                        :show-selection-controls="!!(activeSelectionIds.length && state.selectedElementId !== 'background')"
                        :show-marquee="selectionMarquee.active"
                        :show-group-button="multiSelectionIds.length > 1"
                        :show-edit-text-button="selectedElementType === 'text'"
                        :show-clone-button="canCloneCurrentSelection"
                        :overlay-control-target-id="overlayControlTargetId"
                        :is-group-selection="isGroupSelection"
                        :has-multi-selection="hasMultiSelection"
                        :selected-element-type="selectedElementType"
                        :selected-action-bar-style="selectedActionBarStyle"
                        :selected-overlay-style="selectedOverlayStyle"
                        :selected-handle-metrics="selectedHandleMetrics"
                        :control-zoom-style="controlZoomStyle"
                        :marquee-rect-style="marqueeRectStyle"
                        @mark-editor-control-interaction="markEditorControlInteraction"
                        @group-selected-elements="groupSelectedElements"
                        @edit-selected-text-element="editSelectedTextElement"
                        @clone-current-selection="cloneCurrentSelection"
                        @delete-current-selection="deleteCurrentSelection"
                        @start-rotate="startRotate($event.event, $event.id)"
                        @reset-rotation="resetRotation"
                        @start-resize="startResize($event.event, $event.id, $event.handle)"
                      />
                      <!-- Guías de alineación -->
                      <div v-if="documentPage.id === workingDocumentPageId && guides.length" class="pointer-events-none absolute inset-0 z-[5000]">
                        <div
                          v-for="(guide, index) in guides"
                          :key="`guide-${index}`"
                          class="absolute bg-primary/70"
                          :style="guide.type === 'vertical'
                            ? { left: `${guide.x}px`, top: `${guide.start}px`, width: '1px', height: `${guide.end - guide.start}px` }
                            : { left: `${guide.start}px`, top: `${guide.y}px`, width: `${guide.end - guide.start}px`, height: '1px' }"
                        ></div>
                      </div>
                    </template>
                  </EditorCanvasStage>
                </div>
                <div
                  v-if="isBrochureDocument()"
                  class="mt-2 grid grid-cols-2 gap-2 text-center text-xs font-semibold text-slate-500 dark:text-slate-300"
                  @pointerdown.stop
                >
                  <span
                    v-for="label in brochurePanelLabels(pageIndex)"
                    :key="`${documentPage.id}-${label}`"
                    class="rounded-full border border-base-300 bg-base-100/90 px-3 py-1 shadow-sm"
                  >
                    {{ label }}
                  </span>
                </div>
                </div>
              </section>

              <div class="relative w-full" :style="addPageButtonViewportStyle">
                <button type="button" class="btn btn-outline btn-primary absolute top-0 left-1/2 origin-top" :style="pageChromeStyle" @pointerdown.stop @click.stop.prevent="addDocumentPage()">
                {{ addPageButtonLabel }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
    </section>
    <!-- Diálogo de asistente -->
    <dialog v-if="assistantOpen" class="modal modal-open backdrop-blur-sm" style="z-index:10000;">
      <div class="modal-box w-full max-w-lg lg:max-w-5xl p-0 overflow-visible bg-base-100 rounded-[30px] shadow-2xl border border-base-300">
        <DesignerAssistant
          :step="assistantStep"
          :show-footer="true"
          :show-close="true"
          :show-step-navigation="false"
          :hide-templates-step="isTemplateBaseEditor"
          @close="closeAssistant"
          @finish="handleAssistantFinish"
        />
      </div>
    </dialog>
    </div>
  </DesignerLayout>
</template>

<style>
@keyframes editor-pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(103, 232, 249, 0.5), 0 0 0 4px rgba(103, 232, 249, 0.15);
  }
  50% {
    box-shadow: 0 0 0 5px rgba(103, 232, 249, 0.2), 0 0 0 10px rgba(103, 232, 249, 0);
  }
}
.editor-editing-pulse {
  animation: editor-pulse 1.4s ease-in-out infinite;
}
</style>
