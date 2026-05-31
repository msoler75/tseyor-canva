#!/usr/bin/env node

/**
 * tc_render.js — Headless Renderer (.tc → PNG)
 *
 * Part of the Smart Import Calibration Pipeline.
 * Uses Playwright to launch a headless Chromium, inject a .tc design into
 * the Tseyor Canva editor, and screenshot the rendered canvas.
 *
 * Usage:
 *   node scripts/smart-import/tc_render.js --tc <path> --output <path>
 *
 * Dependencies:
 *   - PHP 8.1+ with Composer dependencies installed
 *   - MySQL/MariaDB running (Laravel app requires DB)
 *   - Node 20+ with Playwright installed (npx playwright install chromium)
 *   - The app build must exist (public/build/) — will auto-rebuild if missing
 *
 * Environment variables (optional):
 *   TC_RENDER_PORT     Port for the PHP dev server (default: 8080)
 *   TC_RENDER_TIMEOUT  Max seconds to wait for render (default: 30)
 *   TC_RENDER_HOST     Host for the PHP dev server (default: localhost)
 */

import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { existsSync, readFileSync, mkdirSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { get } from 'node:http';

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const PROJECT_ROOT = resolve(import.meta.dirname, '../..');
const PUBLIC_DIR = resolve(PROJECT_ROOT, 'public');
const BUILD_DIR = resolve(PUBLIC_DIR, 'build');
const LARAVEL_SERVER_PHP = resolve(
  PROJECT_ROOT,
  'vendor/laravel/framework/src/Illuminate/Foundation/resources/server.php',
);
const PORT = parseInt(process.env.TC_RENDER_PORT ?? '8080', 10);
const HOST = process.env.TC_RENDER_HOST ?? 'localhost';
const RENDER_TIMEOUT_MS =
  parseInt(process.env.TC_RENDER_TIMEOUT ?? '30', 10) * 1000;
const SERVER_START_TIMEOUT_MS = 15_000;
const BASE_URL = `http://${HOST}:${PORT}`;

// ---------------------------------------------------------------------------
// Argument parsing
// ---------------------------------------------------------------------------

function parseArgs() {
  const args = process.argv.slice(2);
  const opts = { tcPath: null, outputPath: null };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--tc':
        opts.tcPath = resolve(process.cwd(), args[++i]);
        break;
      case '--output':
        opts.outputPath = resolve(process.cwd(), args[++i]);
        break;
      case '--help':
      case '-h':
        printHelp();
        process.exit(0);
      default:
        if (args[i].startsWith('--')) {
          console.error(`❌ Unknown option: ${args[i]}`);
          printHelp();
          process.exit(1);
        }
    }
  }

  if (!opts.tcPath) {
    console.error('❌ Missing required argument: --tc <path>');
    printHelp();
    process.exit(1);
  }
  if (!opts.outputPath) {
    console.error('❌ Missing required argument: --output <path>');
    printHelp();
    process.exit(1);
  }

  return opts;
}

function printHelp() {
  console.log(`
tc_render.js — Headless Renderer (.tc → PNG)

Usage:
  node scripts/smart-import/tc_render.js --tc <path> --output <path>

Options:
  --tc <path>      Path to the .tc design file (required)
  --output <path>  Path for the output PNG screenshot (required)
  --help, -h       Show this help message

Environment:
  TC_RENDER_PORT     Port for the PHP dev server (default: 8080)
  TC_RENDER_TIMEOUT  Max seconds to wait for render (default: 30)
  TC_RENDER_HOST     Host for the PHP dev server (default: localhost)
`);
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Check if a URL responds with a given status range */
function urlReady(url, retries = 30, delayMs = 500) {
  return new Promise((resolve, reject) => {
    let attempts = 0;
    const check = () => {
      attempts++;
      const req = get(url, (res) => {
          res.resume();
          // Accept any 2xx/3xx (page might redirect or have minor issues)
          if (res.statusCode >= 200 && res.statusCode < 400) {
            resolve(true);
          } else if (attempts < retries) {
            setTimeout(check, delayMs);
          } else {
            reject(
              new Error(
                `Server responded with status ${res.statusCode} after ${attempts} attempts`,
              ),
            );
          }
        })
        .on('error', () => {
          if (attempts < retries) {
            setTimeout(check, delayMs);
          } else {
            reject(
              new Error(
                `Server not reachable at ${url} after ${attempts} attempts`,
              ),
            );
          }
        });
    };
    check();
  });
}

/** Read and parse a .tc file */
function readTcFile(tcPath) {
  if (!existsSync(tcPath)) {
    throw new Error(`.tc file not found: ${tcPath}`);
  }
  const raw = readFileSync(tcPath, 'utf-8');
  let data;
  try {
    data = JSON.parse(raw);
  } catch {
    throw new Error(`Invalid JSON in .tc file: ${tcPath}`);
  }
  if (!data.tcVersion) {
    throw new Error(`.tc file is missing tcVersion field: ${tcPath}`);
  }
  return data;
}

/** Ensure the Vite build exists; rebuild if missing */
function ensureBuild() {
  if (existsSync(BUILD_DIR)) {
    console.log('✓ Build found at public/build/');
    return Promise.resolve();
  }

  console.log('⚠ Build not found. Running npm run build...');
  return new Promise((resolvePromise, reject) => {
    const proc = spawn('npm', ['run', 'build'], {
      cwd: PROJECT_ROOT,
      stdio: ['ignore', 'inherit', 'inherit'],
      shell: true,
    });
    proc.on('close', (code) => {
      if (code === 0) {
        console.log('✓ Build completed');
        resolvePromise();
      } else {
        reject(new Error(`npm run build failed with exit code ${code}`));
      }
    });
    proc.on('error', (err) => reject(err));
  });
}

/** Start the PHP/Laravel dev server */
function startPhpServer() {
  if (!existsSync(LARAVEL_SERVER_PHP)) {
    throw new Error(
      `Laravel server.php not found at ${LARAVEL_SERVER_PHP}. ` +
        'Run composer install first.',
    );
  }

  console.log(`Starting PHP dev server on ${HOST}:${PORT}...`);

  const proc = spawn(
    'php',
    [
      '-S',
      `${HOST}:${PORT}`,
      '-t',
      PUBLIC_DIR,
      LARAVEL_SERVER_PHP,
    ],
    {
      cwd: PROJECT_ROOT,
      stdio: ['ignore', 'pipe', 'pipe'],
      env: { ...process.env },
    },
  );

  // Capture stderr for diagnostics (PHP built-in server logs there)
  const stderrChunks = [];
  proc.stderr.on('data', (chunk) => stderrChunks.push(chunk));

  // Log stdout only if verbose
  proc.stdout.on('data', (chunk) => {
    const msg = chunk.toString().trim();
    if (msg) console.log(`  [php-srv] ${msg}`);
  });

  proc.on('error', (err) => {
    throw new Error(`Failed to start PHP server: ${err.message}`);
  });

  return proc;
}

/** Check if the server response indicates a functional page (not a 500 error) */
async function checkPageHealthy(url) {
  return new Promise((resolvePromise) => {
    const req = get(url, (res) => {
        res.resume();
        // If status is 200-399, page loaded
        // If 500, something is wrong (likely DB)
        resolvePromise(res.statusCode >= 200 && res.statusCode < 400);
      })
      .on('error', () => {
        resolvePromise(false);
      });
  });
}

// ---------------------------------------------------------------------------
// Main render flow
// ---------------------------------------------------------------------------

async function render(tcPath, outputPath) {
  // 1. Read and validate .tc
  console.log(`Reading .tc file: ${tcPath}`);
  const tcContent = readTcFile(tcPath);
  console.log(
    `✓ .tc loaded (tcVersion: ${tcContent.tcVersion}, designSurface: ${tcContent.designSurface?.width ?? '?'}×${tcContent.designSurface?.height ?? '?'})`,
  );

  // 2. Ensure build exists
  await ensureBuild();

  // 3. Start PHP server (or fail fast)
  let serverProcess = null;
  let serverStarted = false;

  try {
    serverProcess = startPhpServer();
    await urlReady(BASE_URL, 30, 500);
    serverStarted = true;
    console.log('✓ PHP dev server is ready');
  } catch (err) {
    if (serverProcess) {
      serverProcess.kill();
    }
    throw new Error(
      `Could not start PHP dev server.\n` +
        `  Make sure MySQL/MariaDB is running and the app is configured.\n` +
        `  Details: ${err.message}`,
    );
  }

  // 4. Verify the editor page loads correctly (no 500 from DB issues)
  const editorUrl = `${BASE_URL}/designer/editor`;
  const isHealthy = await checkPageHealthy(editorUrl);
  if (!isHealthy) {
    serverProcess.kill();
    throw new Error(
      `Editor page at ${editorUrl} returned an error (likely DB connection).\n` +
        `  Make sure MySQL/MariaDB is running and the .env has the correct credentials.\n` +
        `  Try: http://localhost:${PORT}/designer/editor in your browser to check.`,
    );
  }
  console.log('✓ Editor page is reachable');

  // 5. Launch Playwright
  console.log('Launching headless Chromium...');
  const browser = await chromium.launch({
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
    ],
  });

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    ignoreHTTPSErrors: true,
  });

  const page = await context.newPage();

  try {
    // 6. Inject .tc into sessionStorage BEFORE the page JavaScript runs.
    //    This ensures EditorPage.vue's onMounted finds the data immediately.
    await page.addInitScript((content) => {
      try {
        sessionStorage.setItem('importedTcDesign', content);
      } catch (e) {
        console.error('[init] Failed to set sessionStorage:', e);
      }
    }, JSON.stringify(tcContent));

    // 7. Navigate to the editor with the import trigger
    console.log('Navigating to editor with ?imported=tc...');
    await page.goto(`${BASE_URL}/designer/editor?imported=tc`, {
      waitUntil: 'domcontentloaded',
      timeout: RENDER_TIMEOUT_MS,
    });

    // 8. Wait for the canvas element to be visible
    console.log('Waiting for canvas element [data-editor-canvas="true"]...');
    const canvasSelector = '[data-editor-canvas="true"]';
    await page.waitForSelector(canvasSelector, {
      state: 'visible',
      timeout: RENDER_TIMEOUT_MS,
    });
    console.log('✓ Canvas element found');

    // 9. Wait for network to settle (images, data URIs loading)
    await page.waitForLoadState('networkidle', { timeout: RENDER_TIMEOUT_MS });

    // 10. Additional wait for async rendering (data URI images, font loading)
    await page.waitForTimeout(2000);

    // 11. Screenshot the canvas element
    console.log(`Taking screenshot → ${outputPath}`);
    const canvas = await page.$(canvasSelector);
    if (!canvas) {
      throw new Error('Canvas element disappeared before screenshot');
    }

    // Ensure the output directory exists
    mkdirSync(dirname(outputPath), { recursive: true });

    await canvas.screenshot({
      path: outputPath,
      type: 'png',
    });

    // Verify the output file
    const { statSync } = await import('node:fs');
    const stats = statSync(outputPath);
    if (stats.size === 0) {
      throw new Error('Screenshot was created but is empty (0 bytes)');
    }

    console.log(`✓ Screenshot saved: ${outputPath} (${(stats.size / 1024).toFixed(1)} KB)`);
  } finally {
    // 12. Cleanup: close browser
    await browser.close();
    console.log('✓ Browser closed');
  }

  return serverProcess;
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

async function main() {
  const opts = parseArgs();

  let serverProcess = null;

  try {
    serverProcess = await render(opts.tcPath, opts.outputPath);
    console.log('\n✓ Render completed successfully');
  } catch (err) {
    console.error(`\n❌ Render failed: ${err.message}`);
    process.exitCode = 1;
  } finally {
    // Always stop the PHP server
    if (serverProcess) {
      serverProcess.kill('SIGTERM');
      // Give it a moment to shut down gracefully
      await new Promise((r) => setTimeout(r, 500));
      if (!serverProcess.killed) {
        serverProcess.kill('SIGKILL');
      }
      console.log('✓ PHP dev server stopped');
    }
  }
}

main();
