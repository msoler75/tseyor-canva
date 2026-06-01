#!/usr/bin/env node
import { chromium } from 'playwright';
import { readFileSync } from 'node:fs';
import { createAppServer } from './serve-app.mjs';

const PORT = 8193;
const server = createAppServer();
server.listen(PORT, '127.0.0.1', () => {
  console.log(`[debug] Server on http://127.0.0.1:${PORT}`);
});

const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

page.on('console', msg => console.log(`[browser] ${msg.type()}: ${msg.text()}`));
page.on('pageerror', err => console.log(`[browser] ERROR: ${err.message}`));

const tc = readFileSync('./output/google-gemini-2-5-flash/poster-simple/design.tc', 'utf-8');

await page.addInitScript((content) => {
  sessionStorage.setItem('importedTcDesign', content);
}, tc);

await page.goto(`http://127.0.0.1:${PORT}/designer/editor?imported=tc`, {
  waitUntil: 'networkidle',
  timeout: 30000,
});

await page.waitForTimeout(3000);

await page.screenshot({ path: '../render-debug.png', type: 'png', fullPage: true });
console.log('[debug] Screenshot saved to render-debug.png');

const hasCanvas = await page.evaluate(() =>
  document.querySelectorAll('[data-editor-canvas="true"]').length > 0
);
console.log('[debug] Canvas found:', hasCanvas);

if (!hasCanvas) {
  const bodyText = await page.evaluate(() => document.body.innerText.substring(0, 1000));
  console.log('[debug] Body text:', bodyText);
}

await browser.close();
server.close();
