#!/usr/bin/env node

/**
 * render_page.mjs — Generic HTML page → PNG renderer.
 *
 * Loads a local HTML file in Playwright and produces a PNG screenshot.
 *
 * Usage:
 *   node render_page.mjs --input <path> --output <path>
 */

import { chromium } from 'playwright';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

function parseArgs() {
  const args = process.argv.slice(2);
  const opts = { inputPath: null, outputPath: null };
  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--input': opts.inputPath = resolve(process.cwd(), args[++i]); break;
      case '--output': opts.outputPath = resolve(process.cwd(), args[++i]); break;
    }
  }
  if (!opts.inputPath || !opts.outputPath) {
    console.error('Usage: node render_page.mjs --input <path> --output <path>');
    process.exit(1);
  }
  return opts;
}

async function main() {
  const opts = parseArgs();

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
  });

  try {
    const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

    await page.goto('file://' + opts.inputPath, {
      waitUntil: 'networkidle',
      timeout: 30000,
    });

    // Wait for fonts and layout to settle
    await page.waitForTimeout(2000);

    // Screenshot the full page
    await page.screenshot({ path: opts.outputPath, type: 'png', fullPage: true });

    const { statSync } = await import('node:fs');
    const stats = statSync(opts.outputPath);
    console.log(`[OK] Render saved: ${opts.outputPath} (${(stats.size / 1024).toFixed(1)} KB)`);
  } finally {
    await browser.close().catch(() => {});
  }
}

main().catch(err => {
  console.error('[ERROR]', err.message);
  process.exit(1);
});
