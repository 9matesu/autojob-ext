// Landing contract tests. Run from site/test: node --test landing.test.mjs
import { readFileSync, existsSync } from 'node:fs';
import { test } from 'node:test';
import assert from 'node:assert';

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');

test('pt-BR + meta viewport + title resuMe', () => {
  assert.match(html, /<html lang="pt-BR">/);
  assert.match(html, /name="viewport"/);
  assert.match(html, /<title>resuMe/);
});
test('CTA de download aponta para o release v1.0.0', () => {
  assert.match(html, /releases\/download\/v1\.0\.0\/resuMe-1\.0\.0-windows-x64\.zip/);
  const ctaCount = (html.match(/baixar-cta/g) || []).length;
  assert.ok(ctaCount >= 2, 'CTA deve aparecer ao menos 2x (hero + rodapé)');
});
test('video demo referenciado com poster e autoplay muted', () => {
  assert.match(html, /<video[^>]+assets\/demo\.mp4/);
  assert.match(html, /poster="assets\/demo-poster\.jpg"/);
  assert.match(html, /autoplay/); assert.match(html, /muted/); assert.match(html, /loop/);
});
test('arquivos de asset existem no disco', () => {
  for (const f of ['../assets/demo.mp4', '../assets/demo-poster.jpg',
                   '../landing.css', '../landing.js'])
    assert.ok(existsSync(new URL(f, import.meta.url)), f + ' missing');
});
test('zero Google Fonts; Switzer via Fontshare; OFL locais', () => {
  assert.doesNotMatch(html, /fonts\.googleapis|fonts\.gstatic/);
  assert.match(html, /api\.fontshare\.com/);
  assert.match(html, /schibsted-grotesk\.woff2/);
});
test('FAQ usa details/summary (acessível, sem JS)', () => {
  assert.match(html, /<details/); assert.match(html, /<summary/);
});
test('respeita prefers-reduced-motion e tem barra sticky mobile', () => {
  const css = readFileSync(new URL('../landing.css', import.meta.url), 'utf8');
  assert.match(css, /prefers-reduced-motion:\s*reduce/);
  assert.match(css, /\.sticky-bar/);
  const js = readFileSync(new URL('../landing.js', import.meta.url), 'utf8');
  assert.match(js, /IntersectionObserver/);
});
test('sem jargão técnico nem prova social fabricada', () => {
  assert.doesNotMatch(html, /native host|sidecar|FastAPI|SQLite/i);
  assert.match(html, /TODO-PROVA-SOCIAL/); // slot explicitamente vazio
  assert.doesNotMatch(html, /\d+[\d.]*\s*(mil|k usuários|usuários ativos|downloads)/i);
});
