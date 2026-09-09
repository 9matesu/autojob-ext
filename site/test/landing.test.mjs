// resuMe landing v3 contracts. Run from site/test: node --test landing.test.mjs
import { readFileSync, existsSync } from 'node:fs';
import { test } from 'node:test';
import assert from 'node:assert';

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const css = readFileSync(new URL('../landing.css', import.meta.url), 'utf8');
const js = readFileSync(new URL('../landing.js', import.meta.url), 'utf8');

test('pt-BR + meta viewport + title resuMe', () => {
  assert.match(html, /<html lang="pt-BR">/);
  assert.match(html, /name="viewport"/);
  assert.match(html, /<title>resuMe/);
});
test('CTA de download aponta para o release v1.0.0 (>=2x)', () => {
  assert.match(html, /releases\/download\/v1\.0\.0\/resuMe-1\.0\.0-windows-x64\.zip/);
  assert.ok((html.match(/baixar-cta/g) || []).length >= 2);
});
test('V3: hero full — video cobre toda a box, gradiente L->R, texto na extrema esquerda', () => {
  assert.match(html, /class="hero-bg"[\s\S]{0,400}?assets\/demo\.mp4/);
  assert.match(html, /class="hero-bg"[\s\S]{0,400}?>\s*<video[^>]+muted[^>]+autoplay[^>]+loop[^>]+playsinline/);
  assert.match(html, /class="hero-scrim"/);
  assert.match(css, /\.hero-scrim\s*\{[^}]*linear-gradient\(to right, rgba\(0,\s*0,\s*0/);
  assert.match(css, /\.hero-scrim\s*\{[^}]*z-index:\s*1/);
  assert.match(css, /\.hero-bg\s*\{[^}]*z-index:\s*0/);
  assert.match(css, /\.hero\s*>\s*\.wrap\s*\{[^}]*z-index:\s*2/);
  // video ocupa TODA a box (inset:0)
  assert.match(css, /\.hero-bg\s*\{[^}]*inset:\s*0[^}]*\}/);
  // texto na extrema esquerda: wrap do hero sem centralizar
  assert.match(css, /\.hero\s*>\s*\.wrap\s*\{[^}]*(margin:\s*0|margin-inline:\s*0|max-width:\s*none)/);
});
test('V3: hero full-bleed (largura total da pagina)', () => {
  assert.match(css, /\.hero\s*\{[^}]*width:\s*100vw/);
  assert.doesNotMatch(css, /\.hero-bg\s*\{[^}]*max-width/);
});
test('V3: paginas de scroll-snap em secoes .page', () => {
  assert.match(css, /scroll-snap-type:\s*y\s+(start|proximity)/);
  assert.match(css, /\.page\s*\{[^}]*scroll-snap-align:\s*start/);
  const pages = (html.match(/class="[^"]*\bpage\b/g) || []).length;
  assert.ok(pages >= 5, `esperava >=5 secoes .page, achei ${pages}`);
});
test('V3: animacao snap-in (overshoot) no reveal', () => {
  assert.match(css, /cubic-bezier\([^)]*1\.[1-9]/, 'easing com overshoot');
});
test('V3: sem glow, sem pulse, sem marquee (nada caforma)', () => {
  assert.doesNotMatch(css, /@keyframes\s+pulse|animation:\s*pulse/i);
  assert.doesNotMatch(css, /text-shadow|filter:\s*blur\(/i);
  assert.doesNotMatch(css, /box-shadow:[^;]*rgba\(255,\s*232,\s*0/i, 'ring amarelo glow');
  assert.doesNotMatch(html, /marquee/i);
});
test('V3: todos os links internos #tem destino existente', () => {
  const anchors = [...html.matchAll(/href="#([\w-]+)"/g)].map((m) => m[1]);
  for (const a of anchors) {
    assert.match(html, new RegExp(`id="${a}"`), `âncora #${a} sem alvo`);
  }
  assert.ok(anchors.length >= 2);
});
test('V3: botoes com estados visiveis e foco acessivel', () => {
  assert.match(css, /\.btn:hover/);
  assert.match(css, /\.btn:active/);
  assert.match(css, /:focus-visible/);
  assert.doesNotMatch(css, /box-shadow:\s*4px 4px 0 rgba\(255,\s*255,\s*255/);
});
test('V3: voice corporativa-parodia presente e copy humanizada', () => {
  assert.match(html, /sinergia/i);
  assert.match(html, /alinhamento/i);
  // humanizer: sem "nao é só X, é Y", sem "revoluciona", sem promessas vazias de IA
  assert.doesNotMatch(html, /n[ãa]o (é|e) (só|so) .{1,40}, (mas )?é/i);
  assert.doesNotMatch(html, /revolucionar|potencialize|desbloqueie seu potencial/i);
});
test('sem jargão técnico nem prova social fabricada', () => {
  assert.doesNotMatch(html, /native host|sidecar|FastAPI|SQLite/i);
  assert.match(html, /TODO-PROVA-SOCIAL/);
  assert.doesNotMatch(html, /\d+[\d.]*\s*(mil|k usuários|usuários ativos|downloads)/i);
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
  assert.match(css, /prefers-reduced-motion:\s*reduce/);
  assert.match(css, /\.sticky-bar/);
  assert.match(js, /IntersectionObserver/);
});
test('V3: landing.js trata reduced-motion e parallax no hero', () => {
  assert.match(js, /\.pause\(\)/);
  assert.match(js, /hero-bg/);
});
test('assets existem no disco e hero-bg.mp4/jpg antigos foram removidos', () => {
  for (const f of ['../assets/demo.mp4', '../assets/demo-poster.jpg',
                   '../landing.css', '../landing.js'])
    assert.ok(existsSync(new URL(f, import.meta.url)), f + ' missing');
  assert.ok(!existsSync(new URL('../assets/hero-bg.mp4', import.meta.url)));
  assert.ok(!existsSync(new URL('../assets/hero-bg.jpg', import.meta.url)));
});
