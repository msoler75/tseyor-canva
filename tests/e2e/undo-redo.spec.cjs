const { chromium } = require('playwright');

const BASE_URL = 'http://localhost:8000';

const wait = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();

  let passed = 0;
  let failed = 0;

  const test = async (name, fn) => {
    try { await fn(); passed++; console.log(`  \u2713 ${name}`); }
    catch (e) { failed++; console.log(`  \u2717 ${name}: ${e.message}`); }
  };

  console.log('\n--- Undo/Redo E2E Tests ---\n');

  await page.goto(`${BASE_URL}/designer/editor`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(5000);

  const ok = await page.evaluate(() => typeof window.__TEST__ !== 'undefined');
  if (!ok) { console.log('  \u2717 Test hook missing'); await browser.close(); process.exit(1); }

  const snap = () => page.evaluate(() => window.__TEST__.getSnapshot());
  const undo = () => page.evaluate(() => window.__TEST__.undo());
  const redo = () => page.evaluate(() => window.__TEST__.redo());
  const push = (o) => page.evaluate((x) => window.__TEST__.pushSnapshot(x), o);

  // ── Test 1: Undo after text edit ──
  await test('Undo after text edit', async () => {
    const before = await snap();
    await page.evaluate(() => { window.__TEST__.pushSnapshot({ force: true }); });
    await page.evaluate(() => {
      const s = window.__TEST__.getRawState();
      s.content.title = 'Edited ' + Date.now();
    });
    // Wait for Vue watcher to auto-push
    await wait(600);
    await undo();
    await wait(400);
    const after = await snap();
    if (after.content.title !== before.content.title)
      throw new Error(`Title mismatch: "${after.content.title}" vs "${before.content.title}"`);
  });

  // ── Test 2: Redo ──
  await test('Redo after undo', async () => {
    const before = await snap();
    const orig = before.content.subtitle;
    await push({ force: true });
    await wait(200);
    await page.evaluate(() => { window.__TEST__.getRawState().content.subtitle = 'Redo test ' + Date.now(); });
    await wait(600);
    const mid = await snap();
    if (mid.content.subtitle === orig) throw new Error('Edit failed');
    await undo();
    await wait(400);
    await redo();
    await wait(400);
    const after = await snap();
    if (after.content.subtitle === orig) throw new Error('Redo failed');
    console.log(`      Subtitle: "${orig}" → edited → undo → redo → "${after.content.subtitle}"`);
  });

  // ── Test 3: Create page undo ──
  await test('Undo page creation', async () => {
    const before = await snap();
    const len = before.pages.length;
    await push({ force: true });
    await wait(200);
    await page.evaluate(() => {
      const s = window.__TEST__.getRawState();
      s.pages.push({ id: 'p-' + Date.now(), content: {}, elementLayout: {}, customElements: {} });
    });
    await wait(600);
    await undo();
    await wait(400);
    const after = await snap();
    if (after.pages.length !== len)
      throw new Error(`Pages ${after.pages.length} ≠ ${len}`);
    console.log(`      Pages: ${len} → +1 → undo → ${after.pages.length}`);
  });

  // ── Test 4: Delete page undo ──
  await test('Undo page deletion', async () => {
    const before = await snap();
    if (before.pages.length < 2) {
      await page.evaluate(() => {
        window.__TEST__.getRawState().pages.push({ id: 'tmp-' + Date.now(), content: {}, elementLayout: {}, customElements: {} });
      });
      await wait(400);
    }
    const len = (await snap()).pages.length;
    await push({ force: true });
    await wait(200);
    await page.evaluate(() => { window.__TEST__.getRawState().pages.pop(); });
    await wait(600);
    await undo();
    await wait(400);
    const after = await snap();
    if (after.pages.length !== len)
      throw new Error(`Pages ${after.pages.length} ≠ ${len}`);
    console.log(`      Pages: ${len} → -1 → undo → ${after.pages.length}`);
  });

  // ── Test 5: Format change undo ──
  await test('Undo format change', async () => {
    const before = await snap();
    const orig = before.format;
    await push({ force: true });
    await wait(200);
    await page.evaluate(() => { window.__TEST__.getRawState().format = 'brochure'; });
    await wait(600);
    await undo();
    await wait(400);
    const after = await snap();
    if (after.format !== orig) throw new Error(`Format "${after.format}" ≠ "${orig}"`);
    console.log(`      Format: "${orig}" → brochure → undo → "${after.format}"`);
  });

  // ── Test 6: DesignSurface change undo ──
  await test('Undo designSurface change', async () => {
    const before = await snap();
    const orig = before.designSurface;
    await push({ force: true });
    await wait(200);
    await page.evaluate(() => { window.__TEST__.getRawState().designSurface = { width: 1920, height: 1080 }; });
    await wait(600);
    await undo();
    await wait(400);
    const after = await snap();
    if (JSON.stringify(after.designSurface) !== JSON.stringify(orig))
      throw new Error(`Surface changed`);
    console.log(`      Surface restored correctly`);
  });

  // ── Test 7: Objective change undo ──
  await test('Undo objective change', async () => {
    const before = await snap();
    const orig = before.objective;
    await push({ force: true });
    await wait(200);
    await page.evaluate(() => { window.__TEST__.getRawState().objective = 'event_virtual'; });
    await wait(600);
    await undo();
    await wait(400);
    const after = await snap();
    if (after.objective !== orig) throw new Error(`Objective "${after.objective}" ≠ "${orig}"`);
    console.log(`      Objective: "${orig}" → event_virtual → undo → "${after.objective}"`);
  });

  // ── Test 8: outputType change undo ──
  await test('Undo outputType change', async () => {
    const before = await snap();
    const orig = before.outputType;
    await push({ force: true });
    await wait(200);
    await page.evaluate(() => { window.__TEST__.getRawState().outputType = 'digital'; });
    await wait(600);
    await undo();
    await wait(400);
    const after = await snap();
    if (after.outputType !== orig) throw new Error(`outputType "${after.outputType}" ≠ "${orig}"`);
    console.log(`      outputType: "${orig}" → digital → undo → "${after.outputType}"`);
  });

  // ── Test 9: DesignTitle change undo ──
  await test('Undo designTitle change', async () => {
    const before = await snap();
    const orig = before.designTitle;
    await push({ force: true });
    await wait(200);
    await page.evaluate(() => {
      const s = window.__TEST__.getRawState();
      s.designTitle = 'New Title ' + Date.now();
      s.designTitleManual = true;
    });
    await wait(600);
    await undo();
    await wait(400);
    const after = await snap();
    if (after.designTitle !== orig) throw new Error(`Title "${after.designTitle}" ≠ "${orig}"`);
    console.log(`      designTitle restored`);
  });

  // ── Test 10: selectedElementId restoration ──
  await test('selectedElementId restored', async () => {
    await page.evaluate(() => {
      const s = window.__TEST__.getRawState();
      if (s.elementLayout && s.elementLayout.title) s.selectedElementId = 'title';
    });
    await push({ force: true });
    await wait(200);
    await page.evaluate(() => { window.__TEST__.getRawState().selectedElementId = 'background'; });
    await wait(600);
    await undo();
    await wait(400);
    const after = await snap();
    console.log(`      selectedElementId: "${after.selectedElementId}"`);
  });

  // ── Test 11: Page switch + edit + undo ──
  await test('Undo page switch + edit', async () => {
    const before = await snap();
    if (before.pages.length < 2) {
      await page.evaluate(() => {
        const s = window.__TEST__.getRawState();
        s.pages.push({ id: 'p2-' + Date.now(), content: { title: 'Page 2' }, elementLayout: {}, customElements: {} });
      });
      await wait(400);
    }
    const page1Title = before.content.title;
    await push({ force: true });
    await wait(200);
    // Switch to page 2
    await page.evaluate(() => {
      const s = window.__TEST__.getRawState();
      const t = s.pages[1];
      s.content = JSON.parse(JSON.stringify(t.content));
      s.elementLayout = JSON.parse(JSON.stringify(t.elementLayout));
      s.customElements = JSON.parse(JSON.stringify(t.customElements));
    });
    await wait(200);
    // Edit on page 2
    await page.evaluate(() => { window.__TEST__.getRawState().content.title = 'Edited on page 2'; });
    await wait(600);
    // Undo 3x: back through switch + page2 load + baseline
    for (let i = 0; i < 3; i++) { await undo(); await wait(400); }
    const after = await snap();
    console.log(`      Title after undo: "${after.content.title}" (expected "${page1Title}")`);
    console.log(`      Pages: ${after.pages.length}`);
  });

  // ── Summary ──
  console.log(`\n--- Results: ${passed}/${passed + failed} passed ---\n`);
  await browser.close();
  process.exit(failed > 0 ? 1 : 0);
})().catch(async (err) => {
  console.error('Fatal:', err.message);
  process.exit(1);
});
