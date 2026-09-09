// Chooser contract tests for extension/content.js (static assertions, node --test).
// Run from extension/test: node --test chooser.test.mjs
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import assert from 'node:assert';

const src = readFileSync(new URL('../content.js', import.meta.url), 'utf8');

test('Escape always cancels the whole session (no backToSelection on Esc)', () => {
  const at = src.indexOf('if (e.key === "Escape")');
  assert.ok(at >= 0, 'Escape branch missing');
  const escBlock = src.slice(at, at + 220);
  assert.match(escBlock, /cancel\(null\)/);
  assert.doesNotMatch(escBlock, /backToSelection/);
});

test('capture preview is an editable textarea, not a read-only pre', () => {
  assert.match(src, /createElement\("textarea"\)/);
  assert.doesNotMatch(src, /createElement\("pre"\)/);
});

test('CAPTURAR posts the edited value, not the original text', () => {
  const at = src.indexOf('btnCapture.addEventListener');
  assert.ok(at >= 0);
  const block = src.slice(at, at + 400);
  assert.match(block, /finish\(target,\s*ta\.value\)/);
});

test('pending text tracks edits (getter or input listener)', () => {
  const tracks =
    /get text\(\)\s*\{\s*return ta\.value/.test(src) ||
    /ta\.addEventListener\(\s*"input"[\s\S]{0,120}state\.pending\.text\s*=\s*ta\.value/.test(src);
  assert.ok(tracks, 'state.pending must expose the edited text');
});

test('overlay fonts carry no Google-hosted family (offline-safe)', () => {
  assert.doesNotMatch(src, /Space Mono/);
});
