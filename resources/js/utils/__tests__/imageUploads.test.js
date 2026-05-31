import { describe, it, expect, vi } from 'vitest';
import {
  isDataImageUrl,
  extractImageFilesFromDataTransfer,
  hasFilesInTransfer,
  dataUrlToFile,
  isEditableTarget,
} from '../imageUploads';

describe('isDataImageUrl', () => {
  it('returns true for valid data image URLs', () => {
    expect(isDataImageUrl('data:image/png;base64,iVBOR')).toBe(true);
    expect(isDataImageUrl('data:image/jpeg;base64,/9j/')).toBe(true);
    expect(isDataImageUrl('data:image/svg+xml;utf8,<svg></svg>')).toBe(true);
  });

  it('returns false for non-data URLs', () => {
    expect(isDataImageUrl('https://example.com/image.png')).toBe(false);
    expect(isDataImageUrl('/storage/users/1/img.jpg')).toBe(false);
    expect(isDataImageUrl('')).toBe(false);
  });

  it('returns false for null or undefined', () => {
    expect(isDataImageUrl(null)).toBe(false);
    expect(isDataImageUrl(undefined)).toBe(false);
  });

  it('returns false for non-string values', () => {
    expect(isDataImageUrl(123)).toBe(false);
    expect(isDataImageUrl({})).toBe(false);
  });
});

describe('extractImageFilesFromDataTransfer', () => {
  function createFileItem(file) {
    return {
      kind: 'file',
      type: file.type,
      getAsFile: () => file,
    };
  }

  function createTextItem() {
    return { kind: 'string', type: 'text/plain' };
  }

  it('extracts image files from items', () => {
    const png = new File([''], 'img.png', { type: 'image/png' });
    const jpg = new File([''], 'photo.jpg', { type: 'image/jpeg' });
    const transfer = { items: [createFileItem(png), createFileItem(jpg), createTextItem()] };
    const result = extractImageFilesFromDataTransfer(transfer);
    expect(result).toHaveLength(2);
    expect(result[0].name).toBe('img.png');
    expect(result[1].name).toBe('photo.jpg');
  });

  it('falls back to transfer.files when items is empty', () => {
    const png = new File([''], 'img.png', { type: 'image/png' });
    const txt = new File([''], 'doc.txt', { type: 'text/plain' });
    const transfer = { items: [], files: [png, txt] };
    const result = extractImageFilesFromDataTransfer(transfer);
    expect(result).toHaveLength(1);
    expect(result[0].name).toBe('img.png');
  });

  it('returns empty array for null transfer', () => {
    expect(extractImageFilesFromDataTransfer(null)).toEqual([]);
    expect(extractImageFilesFromDataTransfer(undefined)).toEqual([]);
  });
});

describe('hasFilesInTransfer', () => {
  it('detects files from types array', () => {
    expect(hasFilesInTransfer({ types: ['Files', 'text/html'] })).toBe(true);
  });

  it('detects files from items with kind file', () => {
    const transfer = { types: [], items: [{ kind: 'file' }] };
    expect(hasFilesInTransfer(transfer)).toBe(true);
  });

  it('returns false for text-only transfers', () => {
    const transfer = { types: ['text/plain'], items: [{ kind: 'string' }] };
    expect(hasFilesInTransfer(transfer)).toBe(false);
  });

  it('returns false for null', () => {
    expect(hasFilesInTransfer(null)).toBe(false);
  });
});

describe('dataUrlToFile', () => {
  const dataUrl = 'data:image/png;base64,iVBORw0KGgo=';

  it('converts a data URL to a File object', () => {
    const file = dataUrlToFile(dataUrl, 'test.png');
    expect(file).toBeInstanceOf(File);
    expect(file.name).toBe('test.png');
    expect(file.type).toBe('image/png');
  });

  it('adds extension if filename has none', () => {
    const file = dataUrlToFile(dataUrl, 'test');
    expect(file.name).toBe('test.png');
  });

  it('throws on non-image data URLs', () => {
    expect(() => dataUrlToFile('data:text/plain;base64,ABC')).toThrow();
  });

  it('throws on invalid data URLs', () => {
    expect(() => dataUrlToFile('not-a-data-url')).toThrow();
  });
});

describe('isEditableTarget', () => {
  it('returns true for contenteditable elements', () => {
    const el = document.createElement('div');
    el.setAttribute('contenteditable', 'true');
    expect(isEditableTarget(el)).toBe(true);
  });

  it('returns true for input elements', () => {
    const el = document.createElement('input');
    expect(isEditableTarget(el)).toBe(true);
  });

  it('returns true for textarea elements', () => {
    const el = document.createElement('textarea');
    expect(isEditableTarget(el)).toBe(true);
  });

  it('returns true for descendants of contenteditable', () => {
    const parent = document.createElement('div');
    parent.setAttribute('contenteditable', 'true');
    const child = document.createElement('span');
    parent.appendChild(child);
    expect(isEditableTarget(child)).toBe(true);
  });

  it('returns false for non-editable elements', () => {
    const el = document.createElement('div');
    expect(isEditableTarget(el)).toBe(false);
  });

  it('returns false for non-HTMLElement values', () => {
    expect(isEditableTarget(null)).toBe(false);
    expect(isEditableTarget({})).toBe(false);
  });
});
