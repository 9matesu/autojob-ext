# resuMe Landing Page — Plan

Repo: `I:\autojob\autojob-ext` (branch `master`, remote `9matesu/autojob-ext`).
Remotion project: `I:\remotion-video` (separate repo; comps registered in its root).
Shell: git-bash. Plain PT-BR strings (existing voice).

## Goal

Substituir `site/index.html` por uma landing page moderna do resuMe (mesma
estética yellow/black brutalista, Instrument Serif + Switzer/Schibsted,
animações + vídeo demo em Remotion) 100% focada em leigos baixarem o pacote
portável e começarem — hospedada no GitHub Pages do repo.

## Current context / assumptions

- `site/index.html` hoje: página estática de download sóbria (157 linhas,
  PT-BR, fontes @font-face locais + Switzer via CDN Fontshare). Ela VIRA a
  base da landing (não do zero) — cores e tokens já corretos.
- `dist/resuMe-1.0.0-windows-x64.zip` (~79 MB) existe localmente; NENHUMA
  release/tag `v1.0.0` no GitHub ainda (fase F2 ficou pendente de "go").
  A landing aponta para `https://github.com/9matesu/autojob-ext/releases/download/v1.0.0/resuMe-1.0.0-windows-x64.zip`
  — o link só funciona depois do task L0 (release). Ordem obrigatória.
- Zip de 79 MB NÃO vai no Pages (limite 100 MB total do site + lentidão) —
  download sempre via Release Asset. Pages serve só HTML/CSS/JS/fontes/vídeo.
- Vídeo: mock animado em Remotion (decisão do usuário). ITF-FFL permite uso
  de Switzer em "digital images, video" — o MP4 rasteriza pixels, não embute
  a fonte; legal. Fontes do comp: Switzer local do I:/remotion-video se
  existir, senão baixar woff2 pro comp (OFL Schibsted fallback já no repo).
- Estética canônica (já verificada no código): fundo #FFF, tinta #000,
  amarelo de marca #FFE800 (logo novo), hairline #1a1a1a, sombras duras
  `Npx Npx 0 #000`, cantos retos EXCETO o logo (arredondado), serif = título
  editorial (Instrument Serif), sans = funcional.
- "MRR alto" foi resolvido como Free-only: SEM fabricated testimonials/social
  proof. Slots de prova social entram como comentários HTML marcados
  `TODO-PROVA-SOCIAL` para preencher com depoimentos reais depois. Nunca
  inventar números de usuários (regra do projeto: honestidade).
- Páginas do projeto via GitHub Actions (workflow novo). Sem framework JS
  (YAGNI: 1 página estática + IntersectionObserver).
- Usuário leigo: CTA único repetido, zero jargão ("native host", "sidecar"
  não aparecem na landing; "motor local" sim), passos numerados gigantes,
  FAQ respondendo medo (vírus? pago? precisa conta? macOS?).

## Architecture

`site/` ganha `landing.css` + `landing.js` (DRY com o `index.html` atual,
que é reescrito como a landing), um `assets/demo.mp4` + `assets/demo-poster.jpg`
renderizados por um comp novo `ResumeDemo` no `I:\remotion-video`, e um
workflow `.github/workflows/pages.yml` que publica `site/` no Pages. Testes:
`site/test/landing.test.mjs` (assertions estáticos, padrão `chooser.test.mjs`
já existente no repo — node --test, sem deps).

---

## Phase L0 — Release no GitHub (pré-requisito do link de download)

Mutação externa — executar SOMENTE quando o usuário disser go (ele já disse
"go" para a execução deste plano; confirmar push+release no momento de rodar).

```bash
cd /i/autojob/autojob-ext
git push origin master
git tag v1.0.0 && git push origin v1.0.0
gh release create v1.0.0 dist/resuMe-1.0.0-windows-x64.zip \
  --title "resuMe 1.0.0" --notes-file CHANGELOG.md
# Expected: "https://github.com/9matesu/autojob-ext/releases/tag/v1.0.0"
curl -sI https://github.com/9matesu/autojob-ext/releases/download/v1.0.0/resuMe-1.0.0-windows-x64.zip | head -1
# Expected: HTTP/2 302 (redirect p/ asset storage = link vivo)
```

## Phase L1 — Testes primeiro (TDD da estática)

### Task L1.1 — Testes falhos

Create `site/test/landing.test.mjs`:

```js
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
```

Run: `cd site/test && node --test landing.test.mjs`
Expected: 8 tests, ≥6 FAIL (RED). Commit: `L1.1: failing landing contract tests`

## Phase L2 — Vídeo demo (Remotion, no I:/remotion-video)

### Task L2.0 — Explorar o projeto (2 min, read-only)

```bash
cd /i/remotion-video && cat package.json | grep -A3 '"scripts"' && ls src
```
Ache onde os comps são registrados (`registerRoot` — ex. `src/index.tsx`);
o comp existente `BlackmesaPost` mostra o padrão.

### Task L2.1 — Comp `ResumeDemo` (mock do fluxo real)

Create `I:/remotion-video/src/ResumeDemo/index.tsx` (ajustar import ao registro
real do repo). Cena 1280×720, 15 s @30fps = 450 frames. 4 cenas:

1. **0–4s BrowserFrame**: janela de navegador fake (chrome cinza-claro, URL
   `gupy.io/vaga/desenvolvedor-full-stack`) com posting de exemplo; cursor
   entra, painel da vaga ganha outline amarelo 3px + label preta
   `article.job-posting · ~2.4k chars` (fiel ao content.js real); ↑/↓ setas
   desenhadas. Fundo branco, tipografia Switzer/Helvetica.
2. **4–8s Editável**: click → toast amarelo bottom-center idêntico ao real
   (barra preta `PRÉVIA DA CAPTURA`, botões ESCOLHER OUTRO/CAPTURAR);
   caret pisca digitando: texto do textarea ganha um `- "Inglês avançado"
   removido` (strike) e um parágrafo some — mostra que é editável.
   `ENTER` keycap pisca → toast fecha.
3. **8–12s Adaptação**: split — esquerda perfil mestre (cards brancos, borda
   2px preta), direita arrow → PDF A4 "devcelio-like" cujo resumo REESCREVE
   com highlight amarelo palavra por palavra (`match 87%` tag amarela sobe).
   Números fictícios? NÃO: usar `match 87%` apenas como UI mock do vídeo —
   aceitável porque é clearly-demo (logo "demo" watermark pequeno no canto).
4. **12–15s Endcard**: logo `Me` (quadrado #FFE800 arredondado, Helvetica
   bold preto tight-kerning — o SVG novo) + wordmark
   `resu` (sans bold) + `Me` (Instrument Serif) + `grátis · 100% no seu PC` +
   `resuMe.github.io` fade-in, corte seco final.

Esqueleto (implementar cenas com `useCurrentFrame` + `interpolate`; fontes
via `@remotion/google-fonts/InstrumentSerif` + woff2 Switzer local com
`staticFile()` — padrão já usado em BlackmesaPost):

```tsx
import { AbsoluteFill, Sequence, useCurrentFrame, interpolate, staticFile } from 'remotion';
export const ResumeDemo: React.FC = () => (
  <AbsoluteFill style={{ backgroundColor: '#fff', fontFamily: 'Switzer, sans-serif' }}>
    <Sequence durationInFrames={120}><SceneBrowser /></Sequence>
    <Sequence from={120} durationInFrames={120}><SceneEditableToast /></Sequence>
    <Sequence from={240} durationInFrames={120}><SceneAdapt /></Sequence>
    <Sequence from={360} durationInFrames={90}><SceneEndcard /></Sequence>
  </AbsoluteFill>
);
```

Registrar no root do projeto (linhas ao lado de `BlackmesaPost`):
`<Composition id="ResumeDemo" component={ResumeDemo} width={1280} height={720} fps={30} durationInFrames={450} />`

### Task L2.2 — Render + assets no site

```bash
cd /i/remotion-video
npx remotion render ResumeDemo out/resume-demo.mp4 --codec=h264 --video-quality=24
npx remotion still ResumeDemo out/resume-demo-poster.jpg --frame=300
ls -la out/resume-demo.mp4    # Expected: existe; manter <12MB (senão subir --video-quality)
cp out/resume-demo.mp4 "I:/autojob/autojob-ext/site/assets/demo.mp4"  # mkdir -p antes
cp out/resume-demo-poster.jpg "I:/autojob/autojob-ext/site/assets/demo-poster.jpg"
```
Verificar visualmente com vision_analyze do poster + frame 10 do mp4.
Commit (nos DOIS repos): `L2: ResumeDemo comp (mock do fluxo: inspetor → prévia editável → PDF)` + `L2: demo.mp4 + poster no site`

## Phase L3 — Landing (código)

### Task L3.1 — `site/landing.css`

Append-style sheet (não duplicar o que já está no <style> inline — MIGRAR o
<style> atual inteiro para cá e deletar o bloco inline do HTML; DRY).
Além dos tokens atuais (`--yellow:#FFE800` atualizar de #ffff00 p/ bater com
o logo novo), adicionar:

```css
/* reveal on scroll */
.reveal { opacity: 0; transform: translateY(24px); transition: opacity .6s ease, transform .6s cubic-bezier(.2,.8,.2,1); }
.reveal.in { opacity: 1; transform: none; }
@media (prefers-reduced-motion: reduce) {
  .reveal { opacity: 1; transform: none; transition: none; }
  .marquee-track { animation: none !important; }
}
/* marquee */
.marquee { overflow: hidden; border-block: 2px solid var(--ink); background: var(--ink); color: var(--yellow); }
.marquee-track { display: flex; gap: 48px; padding: 10px 0; white-space: nowrap;
  animation: marquee 22s linear infinite; font-weight: 700; font-size: 12px; text-transform: uppercase; letter-spacing: .08em; }
@keyframes marquee { to { transform: translateX(-50%); } }
/* hero video */
.demo-frame { border: 2px solid var(--ink); box-shadow: 8px 8px 0 var(--ink); margin-top: 40px; }
.demo-frame video { display: block; width: 100%; height: auto; }
/* sticky download bar (mobile) */
.sticky-bar { position: fixed; inset-inline: 0; bottom: 0; z-index: 50;
  border-top: 2px solid var(--ink); background: var(--paper); padding: 10px 16px;
  display: none; }
@media (max-width: 640px) { .sticky-bar { display: flex; gap: 10px; align-items: center; justify-content: space-between; } body { padding-bottom: 72px; } }
/* steps */
.steps-big { counter-reset: st; display: grid; gap: 0; }
.steps-big .st { display: grid; grid-template-columns: 96px 1fr; gap: 20px; padding: 32px 0; border-bottom: 1px solid var(--hair); }
.steps-big .st::before { counter-increment: st; content: counter(st); font-family: 'Instrument Serif'; font-size: 72px; line-height: 1; }
/* feature cards */
.cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
@media (max-width: 760px) { .cards { grid-template-columns: 1fr; } }
.card { border: 2px solid var(--ink); box-shadow: 4px 4px 0 var(--ink); padding: 20px; background: var(--paper); transition: transform .12s, box-shadow .12s; }
.card:hover { transform: translate(-2px,-2px); box-shadow: 6px 6px 0 var(--ink); }
/* FAQ */
details { border-bottom: 1px solid var(--hair); padding: 4px 0; }
summary { cursor: pointer; font-weight: 600; font-size: 15px; padding: 14px 0; list-style: none; display: flex; justify-content: space-between; }
summary::after { content: "+"; font-weight: 700; }
details[open] summary::after { content: "–"; }
details p { margin: 0 0 14px; font-size: 14px; line-height: 1.7; color: #333; }
/* pricing-free badge */
.free-badge { display: inline-block; background: var(--yellow); border: 2px solid var(--ink); font-weight: 700; font-size: 11px; text-transform: uppercase; letter-spacing: .06em; padding: 4px 10px; }
@keyframes pulse { 0%,100% { box-shadow: 4px 4px 0 var(--ink); } 50% { box-shadow: 4px 4px 0 var(--ink), 0 0 0 6px rgba(255,232,0,.55); } }
.baixar-cta.hero { animation: pulse 2.6s ease-in-out infinite; }
@media (prefers-reduced-motion: reduce) { .baixar-cta.hero { animation: none; } }
```

### Task L3.2 — `site/landing.js`

```js
// resuMe landing — reveal on scroll + smooth anchor. No deps.
const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
if (!reduce && 'IntersectionObserver' in window) {
  const io = new IntersectionObserver(
    (es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } }),
    { threshold: 0.15 });
  document.querySelectorAll('.reveal').forEach((el) => io.observe(el));
} else {
  document.querySelectorAll('.reveal').forEach((el) => el.classList.add('in'));
}
// count "downloads started" is NOT tracked here (no telemetry — privacy promise)
```

### Task L3.3 — `site/index.html` rewrite

Estrutura completa (escrever integral; conteúdo PT-BR abaixo é o texto final):

1. `<head>`: title `resuMe — seu currículo adaptado a cada vaga`, OG tags
   (`og:image` → assets/demo-poster.jpg), link rel=icon logo.svg, fontshare
   Switzer (existing line), `<link rel="stylesheet" href="landing.css">`,
   `<script src="landing.js" defer>`.
2. **Header** sticky: wordmark resu<span serif>Me</span> · links Como funciona
   / Perguntas / GitHub · botão pequeno "Baixar grátis".
3. **Hero**: badge `<span class="free-badge">Grátis · sem conta · 100% no seu PC</span>`;
   h1 (serif) `Sua próxima vaga merece um currículo feito para ela.`;
   sub (sans, max 52ch): `O resuMe lê a vaga na tela, adapta seu currículo em
   LaTeX e gera um PDF pronto para o recrutador — em segundos, sem sair do
   navegador. Você instala uma vez e usa para sempre.`;
   linha de CTA: `a.baixar-cta.hero` "Baixar para Windows — 79 MB, zip" +
   `a.ghost` "Ver como funciona ↓"; meta honesta:
   `Windows 10/11 · Chrome · funciona offline depois de instalado`;
   `.demo-frame` com `<video autoplay muted loop playsinline poster="assets/demo-poster.jpg">`.
4. **Marquee**: track duplicado ×2 com palavras da proposta:
   `CAPTURE DO SITE DA VAGA · EDITE ANTES DE ENVIAR · LATEX PROFISSIONAL ·
   PDF PRONTO PARA ATS · SEUS DADOS NO SEU PC · SEM CONTA · SEM TELMETRIA ·`
5. **Como funciona** — `.steps-big` (3 passos, cada `.st.reveal`):
   1 `Instale em 2 minutos` — baixe o zip, descompacte, arraste a pasta
   `extension` no Chrome (link p/ guia ilustrado docs/INSTALACAO.md).
   2 `Envie seu currículo uma única vez` — PDF, Word ou LaTeX; você revisa
   seção por seção antes de confirmar.
   3 `Navegue e capture` — viu uma vaga? `Alt+Shift+A`, clique no texto,
   ajuste se quiser, baixe o PDF adaptado. (nota "um ESC cancela tudo").
6. **Cards** (`.cards`, 6): Prévia editável (o texto que você aprova é o
   texto que vai); Match honesto (percentual nunca é inflado — a IA não
   inventa experiência); LaTeX de verdade (templates editoriais, PDF ATS);
   Funciona offline (o motor roda no seu PC); Sua IA, sua chave
   (OpenAI/Gemini/Anthropic ou Ollama local); Qualquer site (LinkedIn, Gupy,
   Indeed, Greenhouse).
7. **Prova social** — bloco:
   `<!-- TODO-PROVA-SOCIAL: preencher SOMENTE com depoimentos reais coletados
   depois do lançamento. Nunca inventar. -->` + um parágrafo editorial serif:
   `Feito por quem manda currículo e cansa de reescrever tudo.` (autoria, não
   hype). Test exige o marcador TODO.
8. **Privacidade** (resumo da PRIVACIDADE.md em 4 bullets) + frase-âncora
   serif `Nada do seu currículo vai para servidores nossos — porque não
   existem.`
9. **FAQ** (`<details>`×6): É grátis mesmo? Sim, e o código é aberto (link).
   Preciso de conta ou cartão? Não. Meus dados vão pra algum servidor? Só p/
   IA que VOCÊ configurar (ou nenhuma, com Ollama). Tem para macOS/Linux?
   Windows por enquanto; demais em breve. É seguro? Zip não-assinado
   (SmartScreen: desbloquear) — explicação linkada. A IA inventa currículo?
   Não — regras duras no prompt, e você revisa tudo.
10. **CTA final** `#baixar` (2º `.baixar-cta`) + footer com links
    (GitHub · Extensão · Docs).
11. **`.sticky-bar`** mobile: `resuMe · grátis` + botão "Baixar".

Verify: `cd site/test && node --test landing.test.mjs` → 8/8 pass.
Commit: `L3: landing page (hero+demo, marquee, steps, cards, FAQ, sticky CTA) — 8/8 contract tests`

### Task L3.4 — Visual QA

Abrir o site no browser (browser_exec, file://), verificar: fontes renderizam
offline (DevTools offline), vídeo autoplay loopa, reveal dispara no scroll,
CTA href 302-live (depois de L0), FAQ abre sem JS, reduced-motion funciona.
Print do hero p/ o usuário. Sem commit de código — resultado no commit L4.

## Phase L4 — GitHub Pages

### Task L4.1 — Workflow

Create `.github/workflows/pages.yml`:

```yaml
name: Deploy landing
on:
  push:
    branches: [master]
    paths: ['site/**']
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: true
jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: site
          ignore-crs: false
      - id: deployment
        uses: actions/deploy-pages@v4
```

`touch site/.nojekyll` (commit junto). Pages ainda desabilitado no repo —
first run precisa do toggle (o configure-pages falha com erro claro; então):

```bash
gh api repos/9matesu/autojob-ext/pages -X POST -f 'build_type=workflow'
# Expected: JSON com "status":"built" (pode demorar ~1 min)
gh run watch   # ou gh run list -L1
curl -sI https://9matesu.github.io/autojob-ext/ | head -1   # Expected: HTTP/2 200
```

Update landing footer/OG + README + docs/INSTALACAO + CHANGELOG apontando
`https://9matesu.github.io/autojob-ext/` (e site → link do repo).
Commit: `L4: GitHub Pages via Actions; links da landing canônica`

### Task L4.2 — Smoke final

- Pages 200 + assets do Pages 200 (`/assets/demo.mp4`, `/landing.css`).
- Botão de download (Release) 302. Vídeo < 12 MB. `du -sh site` < 20 MB.
- Lighthouse (chrome devtools) Performance ≥ 90, A11y ≥ 95 — números
  reportados no commit message.

## Tests / validation summary

| Gate | Comando | Esperado |
| --- | --- | --- |
| Contratos da landing | `cd site/test && node --test landing.test.mjs` | 8 pass |
| Chooser (não regredir) | `cd extension/test && node --test chooser.test.mjs` | 5 pass |
| Vídeo no ar | `curl -sIL <pages-url>/assets/demo.mp4 \| grep content-length` | 200, <12 MB |
| Download vivo | `curl -sI <release-asset-url> \| head -1` | HTTP/2 302 |
| Pages | `curl -sI https://9matesu.github.io/autojob-ext/ \| head -1` | HTTP/2 200 |

## Risks / tradeoffs

- **Remotion repo é separado** — mudanças no L2 vivem em I:/remotion-video;
  commit lá e só os artefatos (mp4/jpg) entram em site/ do resuMe. Se o
  render quebrar (fontes), fallback: comp só com Instrument Serif Google
  Fonts loader + system sans no mock.
- **Pages + Actions**: primeira ativação exige um `gh api POST` (mutação
  externa, fora do push já autorizado? pedir ok no momento). Se Pages não
  estiver habilitado na org, erro 403 → habilitar Settings→Pages na web.
- **79 MB zip no Release** — ok, mas se o usuário quiser link "próprio" do
  Pages no futuro, precisa de storage externo; Release é o caminho sem custo.
- **Honestidade**: landing sem prova social real na v1 pode converter menos —
  aceito de propósito; regra anti-fabricação do projeto vence. TODO-PROVA-SOCIAL
  documenta a dívida.
- **"MRR alto" com produto Free**: a landing maximiza download+retenção, que é
  o funil honesto até um Pro real (1.1). Nenhuma section de preço mentirosa.
- Marquee/animation podem enjoar — reduced-motion respeitado, test coberto.

## Open questions

1. Nome do repo p/ URL final: `9matesu.github.io/autojob-ext` (atual) vs
   renomear GitHub p/ `resume` (URLs do CHANGELOG/docs mudam — barulho).
   Plano usa o atual; renomear depois é 302-redirect do GitHub de graça.
2. Watermark "demo" no vídeo — deixar? (plano diz sim, pequeno, honestidade).
3. Quer favicon/`og:image` = logo-ai.png 1024 ou o SVG canônico? Plano: SVG.
