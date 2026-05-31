import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  applyFormatToDimensions,
  parseSizeDetail,
  buildCanvasBackgroundStyle,
  buildElementBoxStyle,
  BASE_TEXT_ELEMENT_IDS,
} from '../editorShared';
import { isHorizontalFormat } from '../../data/designer';

describe('parseSizeDetail', () => {
  it('parses standard size strings', () => {
    expect(parseSizeDetail('1080 × 1080 px')).toEqual({ unit: 'px', width: 1080, height: 1080 });
    expect(parseSizeDetail('1920 × 1080 px')).toEqual({ unit: 'px', width: 1920, height: 1080 });
  });

  it('handles sizes with extra whitespace', () => {
    expect(parseSizeDetail('  800  ×  600  px  ')).toEqual({ unit: 'px', width: 800, height: 600 });
  });

  it('returns default for unparseable strings', () => {
    expect(parseSizeDetail('')).toEqual({ unit: 'px', width: 1080, height: 1080 });
    expect(parseSizeDetail('not-a-size')).toEqual({ unit: 'px', width: 1080, height: 1080 });
  });

  it('returns default for null/undefined', () => {
    expect(parseSizeDetail(null)).toEqual({ unit: 'px', width: 1080, height: 1080 });
    expect(parseSizeDetail(undefined)).toEqual({ unit: 'px', width: 1080, height: 1080 });
  });
});

describe('isHorizontalFormat', () => {
  it('returns true for horizontal formats', () => {
    expect(isHorizontalFormat('horizontal')).toBe(true);
  });

  it('returns false for vertical/square formats', () => {
    expect(isHorizontalFormat('vertical')).toBe(false);
    expect(isHorizontalFormat('square')).toBe(false);
  });

  it('returns false for null', () => {
    expect(isHorizontalFormat(null)).toBe(false);
  });
});

describe('applyFormatToDimensions', () => {
  it('returns dimensions as-is for null format', () => {
    expect(applyFormatToDimensions({ width: 800, height: 600 }, null)).toEqual({ width: 800, height: 600 });
  });

  it('swaps dimensions when format is vertical but dimensions are landscape', () => {
    const result = applyFormatToDimensions({ width: 1920, height: 1080 }, 'vertical');
    expect(result.width).toBeLessThan(result.height);
    expect(result.width).toBe(1080);
    expect(result.height).toBe(1920);
  });

  it('returns null for null dimensions', () => {
    expect(applyFormatToDimensions(null, 'horizontal')).toBeNull();
  });
});

describe('BASE_TEXT_ELEMENT_IDS', () => {
  it('contains standard text element keys', () => {
    expect(BASE_TEXT_ELEMENT_IDS).toContain('title');
    expect(BASE_TEXT_ELEMENT_IDS).toContain('subtitle');
    expect(BASE_TEXT_ELEMENT_IDS).toContain('meta');
  });
});

describe('buildCanvasBackgroundStyle', () => {
  it('builds style with background color', () => {
    const layout = { backgroundColor: '#ff0000' };
    const style = buildCanvasBackgroundStyle(layout);
    expect(style.backgroundColor).toBe('#ff0000');
  });

  it('returns default background color for null layout', () => {
    expect(buildCanvasBackgroundStyle(null)).toEqual({ backgroundColor: '#4338ca' });
  });
});

describe('buildElementBoxStyle', () => {
  it('builds box style from layout', () => {
    const layout = { x: 10, y: 20, w: 100, h: 200 };
    const style = buildElementBoxStyle(layout);
    expect(style.left).toBe('10px');
    expect(style.top).toBe('20px');
  });
});
