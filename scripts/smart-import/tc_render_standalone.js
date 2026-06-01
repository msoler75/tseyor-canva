#!/usr/bin/env node

/**
 * tc_render_standalone.js — .tc to PNG renderer
 *
 * Uses the EXISTING Tseyor Canva Vue app to render .tc designs.
 * NO PHP, NO MySQL, NO Laravel needed.
 * Serves the built app via a minimal Node.js HTTP server, then
 * uses Playwright to load it, inject the .tc, and screenshot.
 *
 * Dependencies: playwright (already in package.json)
 *
 * Usage:
 *   node scripts/smart-import/tc_render_standalone.js --tc <path> --output <path>
 */

import { chromium } from 'playwright';
import { readFileSync, existsSync, mkdirSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { pathToFileURL } from 'node:url';
import { createServer } from 'node:http';

// ── Import the app server ────────────────────────────────────────────────
// Lazy-import our static SPA server (no PHP, no MySQL).
const SERVER_MODULE = pathToFileURL(resolve(import.meta.dirname, 'serve-app.mjs')).href;

let appServer = null;
const PORT = 8192; // deterministic port for child process

function parseArgs() {
  const args = process.argv.slice(2);
  const opts = { tcPath: null, outputPath: null };
  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--tc': opts.tcPath = resolve(process.cwd(), args[++i]); break;
      case '--output': opts.outputPath = resolve(process.cwd(), args[++i]); break;
      case '--help': case '-h':
        console.log('Usage: node tc_render_standalone.js --tc <path> --output <path>');
        process.exit(0);
      default:
        console.error('Unknown option: ' + args[i]);
        process.exit(1);
    }
  }
  if (!opts.tcPath || !opts.outputPath) {
    console.error('Required: --tc <path> --output <path>');
    process.exit(1);
  }
  return opts;
}

/** Start the static SPA server */
function startServer() {
  return new Promise((resolvePromise, reject) => {
    // Dynamically import the server module
    import(SERVER_MODULE).then((mod) => {
      appServer = mod.createAppServer();
      appServer.listen(PORT, '127.0.0.1', () => {
        console.log('[render] App server started on http://127.0.0.1:' + PORT);
        resolvePromise();
      });
      appServer.on('error', reject);
    }).catch(reject);
  });
}

function stopServer() {
  if (appServer) {
    appServer.close();
    appServer = null;
  }
}

async function render(tcPath, outputPath) {
  const raw = readFileSync(tcPath, 'utf-8');
  // Validate JSON
  JSON.parse(raw);

  mkdirSync(dirname(outputPath), { recursive: true });

  // Start the app server
  await startServer();

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
  });

  const BASE_URL = 'http://127.0.0.1:' + PORT;

  try {
    const context = await browser.newContext({
      viewport: { width: 2560, height: 1600 },
      deviceScaleFactor: 2,
      ignoreHTTPSErrors: true,
    });

    const page = await context.newPage();

    // Inject .tc into sessionStorage BEFORE page JS runs.
    // EditorPage.vue reads 'importedTcDesign' in onMounted.
    await page.addInitScript((content) => {
      try {
        sessionStorage.setItem('importedTcDesign', content);
      } catch (e) {
        console.error('[init] Failed to set sessionStorage:', e);
      }
    }, raw);

    // Navigate to the editor with import trigger
    console.log('[render] Navigating to editor...');
    await page.goto(BASE_URL + '/designer/editor?imported=tc', {
      waitUntil: 'domcontentloaded',
      timeout: 60000,
    });

    // Wait for the canvas to appear
    console.log('[render] Waiting for canvas element...');
    const canvasSelector = '[data-editor-canvas="true"]';
    await page.waitForSelector(canvasSelector, {
      state: 'visible',
      timeout: 60000,
    });
    console.log('[render] Canvas element found');

    // Wait for network to settle
    await page.waitForLoadState('networkidle', { timeout: 60000 });

    // Extra wait for async rendering (data URIs, fonts)
    await page.waitForTimeout(2000);

    // Hide selection UI (handles, action bar, floating toolbar)
    await page.addStyleTag({
      content: `[data-editor-control="true"] { display: none !important; }`
    });
    await page.waitForTimeout(200);

    // Deselect elements by clicking the canvas grid background
    await page.evaluate(() => {
      const grid = document.querySelector('.canvas-grid');
      if (grid) {
        const rect = grid.getBoundingClientRect();
        const el = document.elementFromPoint(rect.left + 10, rect.top + 10);
        if (el) el.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }));
      }
    });
    await page.waitForTimeout(300);

    // Screenshot the canvas
    console.log('[render] Taking screenshot -> ' + outputPath);
    const canvas = await page.$(canvasSelector);
    if (!canvas) {
      throw new Error('Canvas element disappeared before screenshot');
    }

    await canvas.screenshot({
      path: outputPath,
      type: 'png',
    });

    const { statSync } = await import('node:fs');
    const stats = statSync(outputPath);
    if (stats.size === 0) {
      throw new Error('Screenshot is empty (0 bytes)');
    }
    console.log('[OK] Render saved: ' + outputPath + ' (' + (stats.size / 1024).toFixed(1) + ' KB)');

    await browser.close();
  } finally {
    // Ensure cleanup
    try { await browser.close(); } catch {}
    stopServer();
  }
}

async function main() {
  const opts = parseArgs();
  try {
    await render(opts.tcPath, opts.outputPath);
    process.exit(0);
  } catch (err) {
    console.error('[ERROR] Render failed: ' + err.message);
    console.error(err.stack);
    stopServer();
    process.exit(1);
  }
}

main();
