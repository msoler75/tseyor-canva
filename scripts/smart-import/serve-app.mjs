#!/usr/bin/env node

import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(__dirname, '../..');
const UPLOADS_DIR = path.join(PROJECT_ROOT, 'public/uploads');

const MIME = {
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
  '.ico': 'image/x-icon',
  '.json': 'application/json',
  '.map': 'application/json',
};

// ── Inertia HTML shell ────────────────────────────────────────────────────

function buildHtmlShell() {
  const manifest = JSON.parse(fs.readFileSync(path.join(PROJECT_ROOT, 'public/build/manifest.json'), 'utf-8'));
  const appEntry = manifest['resources/js/app.js'];
  const cssEntry = manifest['resources/css/app.css'];

  const pageData = JSON.stringify({
    component: 'Designer/EditorPage',
    props: {
      errors: {},
      auth: { user: null, isLocal: true },
      designer: {
        endpoints: { upload: '/designer/uploads' },
        imageUploads: { maxWidth: 2000, maxHeight: 2000, jpegQuality: 90, webpQuality: 85 },
      },
      currentStep: 'editor',
      steps: [],
      navigation: { previous: null, next: null },
    },
    url: '/designer/editor?imported=tc',
    version: '1',
  });

  return `<!DOCTYPE html>
<html lang="es" class="h-full">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TSEYOR Canva</title>
  <link rel="stylesheet" href="/fontsx/fonts.css" crossorigin="anonymous" />
  ${cssEntry ? '<link rel="stylesheet" href="/build/' + cssEntry.file + '" />' : ''}
  <script>window.DESIGNER_FONTS_BASE = "/fontsx";</script>
</head>
<body class="h-full antialiased">
  <script data-page="app" type="application/json">${pageData}</script>
  <div id="app"></div>
  ${appEntry ? '<script type="module" crossorigin src="/build/' + appEntry.file + '"></script>' : ''}
</body>
</html>`;
}

// ── Minimal multipart parser ──────────────────────────────────────────────

function parseMultipart(buffer, boundary) {
  const parts = [];
  const delimiter = `--${boundary}`;
  const buf = Buffer.from(delimiter);
  let start = 0;

  while (start < buffer.length) {
    const idx = buffer.indexOf(buf, start);
    if (idx === -1) break;

    const chunkStart = idx + buf.length;
    let lineEnd = buffer.indexOf(Buffer.from([0x0d, 0x0a]), chunkStart);
    if (lineEnd === -1) break;

    const preamble = buffer.subarray(chunkStart, lineEnd).toString().trim();
    if (preamble === '--') break;

    let pos = lineEnd + 2;
    const headers = {};
    while (pos < buffer.length) {
      const nextLine = buffer.indexOf(Buffer.from([0x0d, 0x0a]), pos);
      if (nextLine === -1) break;
      const line = buffer.subarray(pos, nextLine).toString();
      if (line.length === 0) { pos = nextLine + 2; break; }
      const colonIdx = line.indexOf(':');
      if (colonIdx > 0) {
        const headerKey = line.substring(0, colonIdx).trim().toLowerCase();
        const headerVal = line.substring(colonIdx + 1).trim();
        if (headerKey === 'content-disposition') {
          headerVal.split(';').forEach(p => {
            const eq = p.indexOf('=');
            if (eq > 0) {
              const k = p.substring(0, eq).trim();
              let v = p.substring(eq + 1).trim();
              if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) v = v.slice(1, -1);
              headers[k] = v;
            }
          });
        } else {
          headers[headerKey] = headerVal;
        }
      }
      pos = nextLine + 2;
    }

    const nextDelim = buffer.indexOf(buf, pos);
    if (nextDelim === -1) break;

    const contentEnd = nextDelim > 2 && buffer[nextDelim - 2] === 0x0d && buffer[nextDelim - 1] === 0x0a
      ? nextDelim - 2 : nextDelim;
    const data = buffer.subarray(pos, contentEnd);

    parts.push({ headers, data });
    start = nextDelim;
  }

  return parts;
}

// ── Image upload handler ──────────────────────────────────────────────────

async function handleUpload(req, res) {
  const contentType = req.headers['content-type'] || '';
  const match = contentType.match(/boundary=(?:"([^"]+)"|([^;]+))/i);
  if (!match) {
    res.writeHead(400, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Missing boundary' }));
    return;
  }

  const boundary = match[1] || match[2];
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  const buffer = Buffer.concat(chunks);

  const parts = parseMultipart(buffer, boundary);
  let fileData = null;
  let assetId = null;
  let label = 'Imagen';

  for (const part of parts) {
    const name = part.headers.name;
    if (name === 'file' && part.data.length > 0) {
      fileData = part.data;
      const ext = path.extname(part.headers.filename || '.jpg') || '.jpg';
      label = part.headers.filename || label;
    } else if (name === 'assetId') {
      assetId = part.data.toString('utf-8').trim();
    } else if (name === 'label') {
      label = part.data.toString('utf-8').trim() || label;
    }
  }

  if (!fileData) {
    res.writeHead(400, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'No file found in upload' }));
    return;
  }

  if (!fs.existsSync(UPLOADS_DIR)) fs.mkdirSync(UPLOADS_DIR, { recursive: true });

  const id = assetId || randomUUID();
  const safeName = id.replace(/[^a-zA-Z0-9_-]/g, '_');
  const filename = `${safeName}.jpg`;
  const dest = path.join(UPLOADS_DIR, filename);

  fs.writeFileSync(dest, fileData);
  const url = `/uploads/${filename}`;

  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ url, path: dest, assetId: id }));
}

// ── Create server ─────────────────────────────────────────────────────────

const htmlShell = buildHtmlShell();

function createAppServer() {
  return http.createServer((req, res) => {
    const url = new URL(req.url, 'http://localhost');
    const filePath = path.join(PROJECT_ROOT, 'public', url.pathname);

    // POST /designer/uploads — image upload stub
    if (req.method === 'POST' && url.pathname === '/designer/uploads') {
      handleUpload(req, res).catch(() => {
        res.writeHead(500);
        res.end('Upload failed');
      });
      return;
    }

    // SPA shell for all GET designer routes
    if (req.method === 'GET' && (url.pathname === '/' || url.pathname.startsWith('/designer/'))) {
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(htmlShell);
      return;
    }

    // Static files
    if (req.method === 'GET' && fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
      const ext = path.extname(filePath).toLowerCase();
      const contentType = MIME[ext] || 'application/octet-stream';
      try {
        const content = fs.readFileSync(filePath);
        res.writeHead(200, { 'Content-Type': contentType });
        res.end(content);
      } catch {
        res.writeHead(404);
        res.end('Not found');
      }
      return;
    }

    res.writeHead(404);
    res.end('Not found');
  });
}

export { createAppServer };
export default createAppServer;
