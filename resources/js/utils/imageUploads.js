export const isDataImageUrl = (value) => typeof value === 'string' && value.startsWith('data:image/');

export const fileToDataUrl = (file) => new Promise((resolve, reject) => {
  const reader = new FileReader();

  reader.onload = () => {
    const result = typeof reader.result === 'string' ? reader.result : '';
    if (!result) {
      reject(new Error('No se pudo leer la imagen seleccionada.'));
      return;
    }

    resolve(result);
  };

  reader.onerror = () => {
    reject(reader.error ?? new Error('No se pudo leer la imagen seleccionada.'));
  };

  reader.readAsDataURL(file);
});

export const extractImageFilesFromDataTransfer = (transfer) => {
  if (!transfer) {
    return [];
  }

  const items = Array.from(transfer.items ?? []);
  const fromItems = items
    .filter((item) => item.kind === 'file' && item.type.startsWith('image/'))
    .map((item) => item.getAsFile())
    .filter(Boolean);

  if (fromItems.length) {
    return fromItems;
  }

  return Array.from(transfer.files ?? []).filter((file) => file.type.startsWith('image/'));
};

export const hasFilesInTransfer = (transfer) => {
  if (!transfer) {
    return false;
  }

  const types = Array.from(transfer.types ?? []);
  if (types.includes('Files')) {
    return true;
  }

  return Array.from(transfer.items ?? []).some((item) => item.kind === 'file');
};

export const dataUrlToFile = (dataUrl, filename = 'imagen.png') => {
  if (!isDataImageUrl(dataUrl)) {
    throw new Error('La imagen pendiente no tiene un data URI válido.');
  }

  const [meta, base64] = dataUrl.split(',');
  const mimeMatch = meta.match(/data:([^;]+);base64/i);
  const mime = mimeMatch?.[1] ?? 'image/png';
  const binary = window.atob(base64 ?? '');
  const bytes = new Uint8Array(binary.length);

  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }

  const extension = mime.split('/')[1] || 'png';

  return new File([bytes], filename.includes('.') ? filename : `${filename}.${extension}`, { type: mime });
};

const clampQuality = (value, fallback = 0.95) => {
  const normalized = Number(value);
  if (!Number.isFinite(normalized)) {
    return fallback;
  }

  if (normalized > 1) {
    return Math.min(1, Math.max(0.1, normalized / 100));
  }

  return Math.min(1, Math.max(0.1, normalized));
};

const getSafePositiveInt = (value, fallback) => {
  const normalized = Number(value);
  if (!Number.isFinite(normalized) || normalized <= 0) {
    return fallback;
  }

  return Math.round(normalized);
};

const loadImageElement = (file) => new Promise((resolve, reject) => {
  const objectUrl = URL.createObjectURL(file);
  const image = new Image();

  image.onload = () => {
    URL.revokeObjectURL(objectUrl);
    resolve(image);
  };

  image.onerror = () => {
    URL.revokeObjectURL(objectUrl);
    reject(new Error('No se pudo procesar la imagen seleccionada.'));
  };

  image.src = objectUrl;
});

const renameFileExtension = (filename, mimeType) => {
  const extension = mimeType.split('/')[1] || 'png';
  if (!filename) {
    return `imagen.${extension}`;
  }

  const dotIndex = filename.lastIndexOf('.');
  if (dotIndex <= 0) {
    return `${filename}.${extension}`;
  }

  return `${filename.slice(0, dotIndex)}.${extension}`;
};

export const optimizeImageFile = async (file, options = {}) => {
  if (!(file instanceof File) || !file.type.startsWith('image/')) {
    return file;
  }

  const maxWidth = getSafePositiveInt(options.maxWidth, 2400);
  const maxHeight = getSafePositiveInt(options.maxHeight, 2400);
  const jpegQuality = clampQuality(options.jpegQuality, 0.95);
  const webpQuality = clampQuality(options.webpQuality, 0.95);
  const sourceImage = await loadImageElement(file);

  const width = sourceImage.naturalWidth || sourceImage.width;
  const height = sourceImage.naturalHeight || sourceImage.height;

  if (!width || !height) {
    return file;
  }

  const scale = Math.min(1, maxWidth / width, maxHeight / height);
  const targetWidth = Math.max(1, Math.round(width * scale));
  const targetHeight = Math.max(1, Math.round(height * scale));
  const shouldResize = targetWidth !== width || targetHeight !== height;

  if (!shouldResize) {
    return file;
  }

  const canvas = document.createElement('canvas');
  canvas.width = targetWidth;
  canvas.height = targetHeight;

  const context = canvas.getContext('2d', { alpha: true });
  if (!context) {
    return file;
  }

  context.imageSmoothingEnabled = true;
  context.imageSmoothingQuality = 'high';
  context.drawImage(sourceImage, 0, 0, targetWidth, targetHeight);

  const preferredMime = ['image/jpeg', 'image/png', 'image/webp'].includes(file.type)
    ? file.type
    : 'image/png';
  const quality = preferredMime === 'image/jpeg'
    ? jpegQuality
    : preferredMime === 'image/webp'
      ? webpQuality
      : undefined;

  const blob = await new Promise((resolve) => {
    canvas.toBlob((result) => resolve(result), preferredMime, quality);
  });

  if (!(blob instanceof Blob)) {
    return file;
  }

  const filename = renameFileExtension(file.name, blob.type || preferredMime);

  return new File([blob], filename, {
    type: blob.type || preferredMime,
    lastModified: file.lastModified,
  });
};

export const isEditableTarget = (target) => {
  if (!(target instanceof HTMLElement)) {
    return false;
  }

  return Boolean(
    target.closest('input, textarea, [contenteditable="true"], [contenteditable=""], .tiptap, .ProseMirror')
  );
};
