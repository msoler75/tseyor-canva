#!/usr/bin/env node

/**
 * test_tc_render.js — Integration tests for the headless renderer
 *
 * Tests argument parsing, error handling, and file validation
 * without launching a browser (no Laravel/MySQL required).
 *
 * Usage:
 *   node scripts/smart-import/tests/test_tc_render.js
 */

import { execSync } from 'node:child_process';
import { existsSync, readFileSync, writeFileSync, unlinkSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SMART_IMPORT_DIR = resolve(__dirname, '..');
const PROJECT_ROOT = resolve(SMART_IMPORT_DIR, '../..');
const RENDER_JS = resolve(SMART_IMPORT_DIR, 'tc_render.js');

let pass = 0;
let fail = 0;
const tests = [];

function test(name, fn) {
  tests.push({ name, fn });
}

function assert(label, condition) {
  if (condition) {
    console.log(`  ✅ ${label}`);
    pass++;
  } else {
    console.log(`  ❌ ${label}`);
    fail++;
  }
}

function run(cmd) {
  try {
    const out = execSync(cmd, {
      cwd: PROJECT_ROOT,
      encoding: 'utf8',
      stdio: ['pipe', 'pipe', 'pipe'],
      timeout: 10000,
    });
    return { stdout: out, stderr: '', code: 0 };
  } catch (e) {
    return {
      stdout: e.stdout || '',
      stderr: e.stderr || '',
      code: e.status || 1,
      message: e.message || '',
    };
  }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

console.log('=== tc_render.js Integration Tests ===\n');

// --- 1. Environment checks ---
console.log('[1/5] Checking core dependencies...');

// Node
assert('Node.js available', typeof process.version === 'string');

// tc_render.js exists
assert('tc_render.js found', existsSync(RENDER_JS));

// HTTP readiness checks must use the HTTP client API, not createServer().
{
  const source = readFileSync(RENDER_JS, 'utf8');
  assert(
    'HTTP readiness uses node:http get client',
    source.includes("import { get } from 'node:http'") &&
      !source.includes("import { createServer } from 'node:http'"),
  );
}

// --- 2. Playwright ---
console.log('\n[2/5] Checking Playwright availability...');

assert(
  'Playwright installed (node_modules)',
  existsSync(resolve(PROJECT_ROOT, 'node_modules/playwright/package.json')),
);

// --- 3. Argument parsing ---
console.log('\n[3/5] Testing argument parsing...');

// --help
{
  const result = run(`node "${RENDER_JS}" --help`);
  assert('--help flag displays usage', result.stdout.includes('tc_render.js'));
}

// Missing both args
{
  const result = run(`node "${RENDER_JS}"`);
  const output = result.stderr || (result.code !== 0 ? result.stdout : '');
  assert('Missing --tc reports error', output.includes('Missing required argument'));
}

// --tc without --output
{
  const result = run(`node "${RENDER_JS}" --tc "test.tc"`);
  const output = result.stderr || (result.code !== 0 ? result.stdout : '');
  assert('Missing --output reports error', output.includes('Missing required argument'));
}

// --- 4. Error handling ---
console.log('\n[4/5] Testing error handling...');

// Invalid .tc path
{
  const result = run(`node "${RENDER_JS}" --tc "/nonexistent/file.tc" --output "test.png"`);
  const output = result.stderr || result.stdout || '';
  assert('Invalid --tc path reports not found', output.includes('not found') || output.includes('ENOENT'));
}

// Invalid JSON content
{
  const tmpFile = resolve(SMART_IMPORT_DIR, 'tests', '.invalid_json_test.tc');
  writeFileSync(tmpFile, 'this is not json', 'utf8');
  const result = run(`node "${RENDER_JS}" --tc "${tmpFile}" --output "test.png"`);
  const output = result.stderr || result.stdout || '';
  assert('Invalid JSON content reports error', output.includes('Invalid JSON'));
  unlinkSync(tmpFile);
}

// Missing tcVersion
{
  const tmpFile = resolve(SMART_IMPORT_DIR, 'tests', '.no_version_test.tc');
  writeFileSync(tmpFile, JSON.stringify({ format: 'poster' }), 'utf8');
  const result = run(`node "${RENDER_JS}" --tc "${tmpFile}" --output "test.png"`);
  const output = result.stderr || result.stdout || '';
  assert('Missing tcVersion reports error', output.includes('tcVersion'));
  unlinkSync(tmpFile);
}

// Unknown option
{
  const result = run(`node "${RENDER_JS}" --bogus-flag`);
  const output = result.stderr || result.stdout || '';
  assert('Unknown option reports error', output.includes('Unknown option'));
}

// --- 5. Summary and docs ---
console.log('\n[5/5] Checking render prerequisites...\n');

// PHP check
try {
  const phpOut = execSync('php -v', { encoding: 'utf8', timeout: 5000 });
  const phpVer = phpOut.split('\n')[0].trim();
  assert(`PHP available: ${phpVer}`, true);
} catch {
  assert('PHP not found (needed for full render)', false);
}

console.log(`
  To run a full render (requires full Laravel stack):
    # 1. Ensure MySQL is running
    # 2. Build the frontend
    npm run build

    # 3. Run the renderer:
    node scripts/smart-import/tc_render.js \\
      --tc scripts/smart-import/output/gemini-2.5-flash/img-01/design.tc \\
      --output scripts/smart-import/output/gemini-2.5-flash/img-01/render.png

  Prerequisites for full render:
    - PHP 8.1+ with Composer deps (composer install)
    - MySQL/MariaDB running
    - Node 20+ and Playwright: npx playwright install chromium
    - App build: npm run build

  Manual usage:
    node scripts/smart-import/tc_render.js --tc <path.tc> --output <path.png>
    # Or via wrapper:
    bash scripts/smart-import/tc_render.sh <path.tc> <path.png>
`);

console.log(`=== Results: ${pass} passed, ${fail} failed ===`);
process.exit(fail > 0 ? 1 : 0);
