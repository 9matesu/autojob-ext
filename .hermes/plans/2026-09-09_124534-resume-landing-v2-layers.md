# resuMe Landing v2 — camadas + vídeo de fundo (RCD + ui-ux-pro-max)

Repos: `I:\autojob\autojob-ext` (site em `site/`, Pages no push de `site/**`).
Remotion: `I:\remotion-video` (fontes OFL já em `public/fonts/`, padrão do comp
`src/ResumeDemo.tsx` que pode ser copiado).
Shell: git-bash. Idioma da página: PT-BR.

## Goal

Substituir o hero atual da landing (`site/index.html`) por um hero em
camadas — vídeo de fundo ambiente em loop, scrim, grade e texto na frente —
com copy reescrita sob os princípios Revenue-Centric Design, mantendo a
estética brutalista amarelo/preto e todas as seções que já passam nos testes.

## Current context / assumptions

- Landing v1 no ar em https://matesu.me/autojob-ext/ (deploy automático por
  `.github/workflows/pages.yml` quando `site/**` muda). `site/test/landing.test.mjs`
  tem 8 contratos — a v2 tem que mantê-los passando (a fonte de teste é o
  contrato, não o oposto).
- `assets/demo.mp4` (1 MB, mock do fluxo) existe e é referenciado no hero
  dentro de `.demo-frame`. Na v2 ele **sai do hero e vira a seção
  "Veja funcionando"** (RCD: value first — primeiro o ambiente emocional,
  depois a prova concreta, sem competir com o CTA).
- Fontes: body Switzer via Fontshare CDN (permitido no site próprio) +
  Schibsted/Instrument OFL locais — não mudar nada de tipografia.
- Vínculo de marca (skill `rcd-uiux-refactor`, NÃO-NEGOCIÁVEL): sem gradientes
  coloridos, sem glassmorphism, sem blur; sombras duras; cantos retos; escuro
  apenas como fundo. O hero vira fundo PRETO (cor do vídeo) com texto branco —
  isso é troca de camada, não de marca.
- `/plugin marketplace add` é sintaxe do Claude Code; aqui o equivalentes é
  clonar os dois skills para leitura (fase V0). Nada é executado dos scripts
  dos skills; só os markdowns são lidos e destilados em `site/DESIGN-BRIEF.md`.
- Licença RCD: attribution required + proibido uso em gambling — landing de
  currículo, sem problema; creditar o skill no brief.
- Orçamento de peso: hero-bg.mp4 < 4 MB (hard fail > 6 MB) — vídeo ambiente
  de cores chatas comprime muito; `--video-crf` alto resolve se estourar.

## Architecture

Três fases: (V0) clonar os dois skills e destilar um `site/DESIGN-BRIEF.md`
com as decisões aplicadas; (S1) comp Remotion novo `ResumeHeroBg` — loop
abstrato brutalista seamless de 8s (grid deslizante + tile "Me" gigante +
palavras flutuantes), render mp4/jpg; (S2) reescrever o hero do
`index.html` como pilha de camadas (`.hero-bg` video → `.hero-scrim` preto
semi-opaco → `.hero-grid` pattern → `.wrap` conteúdo) com copy RCD, mover o
demo para seção própria, parallax leve na camada de vídeo, pausa com
reduced-motion — TDD: testes novos primeiro (RED), depois implementação
(GREEN), push ativa o deploy sozinho.

---

## Phase V0 — Skills como referência local

### Task V0.1 — Clonar (read-only, fora do commit de código)

```bash
cd /i/autojob/autojob-ext
mkdir -p .hermes/vendor && cd .hermes/vendor
git clone --depth 1 https://github.com/heliocosta-dev/revenue-centric-design
git clone --depth 1 https://github.com/nextlevelbuilder/ui-ux-pro-max-skill
echo '
# Skills vendorizados para referencia (nao distribuidos)
/.hermes/vendor/
' >> ../.gitignore
ls revenue-centric-design/references/conversion-and-landing-pages.md \
   ui-ux-pro-max-skill/.claude/skills
# Expected: o caminho do RCD existe; o dir .claude/skills lista sub-skills (design/ etc.)
```

### Task V0.2 — Ler e destilar

Read (obrigatório, na ordem):
1. `.hermes/vendor/revenue-centric-design/SKILL.md` (spine de 9 princípios).
2. `.hermes/vendor/revenue-centric-design/references/conversion-and-landing-pages.md`
   (princípios de hero/CTA/proof/awareness).
3. `.hermes/vendor/ui-ux-pro-max-skill/.claude/skills/design/SKILL.md` e os
   `.md` de referência que ele indicar para landing/hero/video/UX de motion
   (a árvore tem catálogo de estilos + guidelines; escolher só o que serve a
   brutalismo-flat + dark hero).

Create `site/DESIGN-BRIEF.md` — tabela curta `princípio → decisão nesta página`
cobrindo no mínimo: dor primeiro no h1; CTA declara resultado+tempo+custo;
value before ask (demo antes de steps); um CTA dominante por dobra (Von
Restorff); prova precisa sem invenção (mantém `TODO-PROVA-SOCIAL`); defaults
decidem pelo usuário (idiom do botão); contraste do texto sobre vídeo ≥ 4.5:1;
reduced-motion; loop do vídeo sem emenda perceptível; crédito de proveniência
dos dois skills no rodapé do brief.

Commit: `V0: DESIGN-BRIEF destilado de revenue-centric-design + ui-ux-pro-max`
(os clones NÃO entram no commit — só o brief.)

## Phase S1 — Vídeo de fundo (Remotion, I:/remotion-video)

### Task S1.1 — Comp `ResumeHeroBg` (loop seamless 8s)

Create `I:/remotion-video/src/ResumeHeroBg.tsx`:

```tsx
import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';

// Loop ambiente brutalista: preto #0A0A0A, grid que desliza 1 celula por loop,
// tile "Me" gigante em outline amarelo derivando em diagonal com WRAP exato,
// palavras uppercase flutuando com pulso senoidal. 1920x1080@30, 240f = 8s.
// Seamless: todos os periodos sao divisores exatos de 240 frames.

const W = 1920;
const H = 1080;
const LOOP = 240;
const YELLOW = '#FFE800';

const FontFaces: React.FC = () => (
  <style>{`
    @font-face { font-family:'Schibsted Grotesk'; font-weight:400 800;
      src: url('${'fonts/schibsted-grotesk.woff2'}') format('woff2'); }
  `}</style>
);

// wrap v em [min,max] para movimento em loop fechado
const wrap = (v: number, min: number, max: number) => {
  const range = max - min;
  return ((((v - min) % range) + range) % range) + min;
};

const GridLayer: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const cell = 90;
  const dx = wrap((frame / LOOP) * cell, 0, cell); // 1 celula exata por loop
  const lines: React.ReactNode[] = [];
  for (let x = -cell + dx; x < W + cell; x += cell) {
    lines.push(<line key={'v' + x} x1={x} y1={0} x2={x} y2={H} stroke="#1c1c1c" strokeWidth={1} />);
  }
  for (let y = -cell; y < H + cell; y += cell) {
    lines.push(<line key={'h' + y} x1={0} y1={y} x2={W} y2={y} stroke="#1c1c1c" strokeWidth={1} />);
  }
  void fps;
  return <svg width={W} height={H} style={{position: 'absolute'}}>{lines}</svg>;
};

const MeTile: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / LOOP; // 0..1, periodos inteiros => loop fechado
  const size = 620;
  const x = wrap(-size + t * (W + 2 * size) * 0.5, -size, W + size * 0.2);
  const y = H / 2 - size / 2 + Math.sin(t * Math.PI * 2) * 60;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 128 128"
      style={{position: 'absolute', left: x, top: y, opacity: 0.28}}
    >
      <rect x={2} y={2} width={124} height={124} rx={22} fill="none" stroke={YELLOW} strokeWidth={3} />
      <text x={64} y={86} textAnchor="middle" fontFamily="Helvetica, Arial, sans-serif"
        fontWeight={700} fontSize={64} letterSpacing={-3} fill="none" stroke={YELLOW} strokeWidth={2}>
        Me
      </text>
    </svg>
  );
};

const WORDS: Array<{t: string; x: number; y: number; s: number; ph: number}> = [
  {t: 'CAPTURE', x: 0.12, y: 0.22, s: 34, ph: 0},
  {t: 'ADAPTE', x: 0.66, y: 0.16, s: 44, ph: 1.2},
  {t: 'COMPILE', x: 0.74, y: 0.62, s: 30, ph: 2.4},
  {t: 'CANDIDATO', x: 0.16, y: 0.74, s: 40, ph: 3.6},
  {t: 'LaTeX', x: 0.47, y: 0.45, s: 54, ph: 4.8},
];

const WordsLayer: React.FC = () => {
  const frame = useCurrentFrame();
  const t = (frame / LOOP) * Math.PI * 2;
  return (
    <AbsoluteFill style={{fontFamily: "'Schibsted Grotesk', sans-serif", fontWeight: 800}}>
      {WORDS.map((w) => (
        <div key={w.t} style={{
          position: 'absolute', left: w.x * W, top: w.y * H, fontSize: w.s,
          letterSpacing: '0.12em', color: '#0A0A0A', WebkitTextStroke: `1.5px ${YELLOW}`,
          opacity: 0.5 + 0.5 * Math.abs(Math.sin(t + w.ph)), // periodo = loop exato
          transform: `translateY(${Math.sin(t * 2 + w.ph) * 8}px)`,
        }}>
          {w.t}
        </div>
      ))}
    </AbsoluteFill>
  );
};

export const ResumeHeroBg: React.FC = () => (
  <AbsoluteFill style={{backgroundColor: '#0A0A0A'}}>
    <FontFaces />
    <GridLayer />
    <MeTile />
    <WordsLayer />
  </AbsoluteFill>
);
```

Registrar em `I:/remotion-video/src/Root.tsx` (ao lado de ResumeDemo):
`import {ResumeHeroBg} from './ResumeHeroBg';`
`<Composition id="ResumeHeroBg" component={ResumeHeroBg} width={1920} height={1080} fps={30} durationInFrames={240} />`

Verify: `cd /i/remotion-video && npx tsc --noEmit` → exit 0.
Commit remotion: `S1.1: ResumeHeroBg (loop ambiente seamless p/ landing v2)`

### Task S1.2 — Render + budget

```bash
cd /i/remotion-video
npx remotion render ResumeHeroBg out/resume-hero-bg.mp4 --codec=h264 --video-crf=30
npx remotion still ResumeHeroBg out/resume-hero-bg.jpg --frame=0
ls -la out/resume-hero-bg.mp4
# Expected: existe; se > 4 MB, re-render com --video-crf=34; HARD FAIL se > 6 MB
mkdir -p /i/autojob/autojob-ext/site/assets
cp out/resume-hero-bg.mp4 /i/autojob/autojob-ext/site/assets/hero-bg.mp4
cp out/resume-hero-bg.jpg /i/autojob/autojob-ext/site/assets/hero-bg.jpg
```

QA visual (vision_analyze): frame 0 e frame 120 — legível como marca, sem
banding; o tile Me não cobre as palavras; loop: diff visual frame 0 vs 239
quase idênticos.

## Phase S2 — Landing v2 (TDD)

### Task S2.1 — Testes novos (RED)

Patch `site/test/landing.test.mjs`: manter os 8 existentes INTACTOS e
adicionar:

```js
test('V2: hero tem video de fundo + scrim + grid', () => {
  assert.match(html, /class="hero-bg"[\s\S]{0,400}?assets\/hero-bg\.mp4/);
  assert.match(html, /class="hero-scrim"/);
  assert.match(html, /class="hero-grid"/);
  assert.match(html, /class="hero-bg"[\s\S]{0,400}?>\s*<video[^>]+muted[^>]+autoplay[^>]+loop[^>]+playsinline/);
  assert.match(html, /hero-bg\.jpg/); // poster do fundo
});
test('V2: ordem das camadas documentada no CSS', () => {
  const css = readFileSync(new URL('../landing.css', import.meta.url), 'utf8');
  assert.match(css, /\.hero-bg\s*\{[^}]*z-index:\s*0/);
  assert.match(css, /\.hero-scrim\s*\{[^}]*z-index:\s*1/);
  assert.match(css, /\.hero-grid\s*\{[^}]*z-index:\s*1/);
  assert.match(css, /\.hero\s*>\s*\.wrap\s*\{[^}]*z-index:\s*2/);
});
test('V2: demo.mp4 virou secao propria "Veja funcionando"', () => {
  assert.match(html, /id="demo"[^>]*>[\s\S]{0,120}?<h2/);
});
test('V2: CTA hero declara resultado e tempo', () => {
  assert.match(html, /class="btn baixar-cta hero"[^>]*>[\s\S]{0,160}?Instale em 2 min/i);
});
test('V2: landing.js pausa o video de fundo em reduced-motion', () => {
  const js = readFileSync(new URL('../landing.js', import.meta.url), 'utf8');
  assert.match(js, /hero-bg[\s\S]{0,200}?\.pause\(\)/);
});
```

Run: `cd site/test && node --test landing.test.mjs`
Expected: 13 tests, os 5 novos FAIL (RED), os 8 antigos pass.
Commit: `S2.1: contratos V2 (hero em camadas, demo->secao, CTA outcome) RED`

### Task S2.2 — CSS: camadas + hero dark

Append ao fim de `site/landing.css` (não editar os tokens existentes — DRY):

```css
/* ===== V2: hero em camadas ===== */
.hero { position: relative; min-height: min(92vh, 880px); display: flex;
  align-items: center; overflow: hidden; color: #fff;
  border-bottom: 2px solid var(--ink); padding: 0; }
.hero > .wrap { position: relative; z-index: 2; padding-block: 96px; }
.hero-bg { position: absolute; inset: 0; z-index: 0; will-change: transform; }
.hero-bg video { width: 100%; height: 100%; object-fit: cover; display: block; }
.hero-scrim { position: absolute; inset: 0; z-index: 1; background: rgba(0,0,0,.62); }
.hero-grid { position: absolute; inset: 0; z-index: 1; opacity: .35; pointer-events: none;
  background-image: linear-gradient(rgba(255,255,255,.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,.05) 1px, transparent 1px);
  background-size: 48px 48px; }
.hero h1 { color: #fff; }
.hero .sub { color: #cfcfcf; }
.hero .meta { color: #9a9a9a; }
.hero .free-badge { background: var(--yellow); color: #000; }
.hero .btn.ghost { background: transparent; color: #fff; border-color: #fff;
  box-shadow: 4px 4px 0 rgba(255,255,255,.9); }
.hero .btn.ghost:hover { background: #fff; color: #000; }
.hero .btn.ghost:active { box-shadow: none; }
@media (max-width: 640px) { .hero { min-height: 100svh; } .hero > .wrap { padding-block: 72px; } }
```

O bloco `.hero { padding: 72px 0 56px; ... }` existente deve ser DELETADO
(deixar só a versão v2 — DRY, sem regra duplicada).

### Task S2.3 — HTML: novo hero + seção demo

No `site/index.html`, substituir o bloco `<section class="hero" ...> ... </section>`
inteiro por:

```html
<section class="hero">
  <div class="hero-bg" aria-hidden="true">
    <video autoplay muted loop playsinline disablepictureinpicture preload="auto"
           poster="assets/hero-bg.jpg" src="assets/hero-bg.mp4"></video>
  </div>
  <div class="hero-scrim" aria-hidden="true"></div>
  <div class="hero-grid" aria-hidden="true"></div>
  <div class="wrap">
    <span class="free-badge">Grátis · sem conta · 100% no seu PC</span>
    <h1>Cada vaga pede um currículo diferente.<br />O resuMe escreve o seu em segundos.</h1>
    <p class="sub">Para quem aplica para vagas online e está cansado de reescrever o
      mesmo currículo: o resuMe lê a vaga na sua tela, adapta seu currículo em LaTeX
      e gera um PDF pronto para o recrutador — sem sair do navegador.</p>
    <div class="cta-row">
      <a class="btn baixar-cta hero"
         href="https://github.com/9matesu/autojob-ext/releases/download/v1.0.0/resuMe-1.0.0-windows-x64.zip">
        Baixar grátis — instala em 2 minutos
      </a>
      <a class="btn ghost" href="#demo">Ver funcionando ↓</a>
    </div>
    <p class="meta cta-note">Windows 10/11 · Google Chrome · roda offline depois de instalado</p>
  </div>
</section>
```

E mover o `<figure class="demo-frame">` atual para dentro de uma seção nova
imediatamente após a marquee:

```html
<section id="demo">
  <div class="wrap">
    <h2>Veja o resuMe em ação</h2>
    <figure class="demo-frame">
      ... video demo.mp4 + figcaption atuais, sem alterar ...
    </figure>
    <p class="meta" style="margin-top:14px">Demonstração animada (simulação) — o fluxo real leva ~30 segundos.</p>
  </div>
</section>
```

Adicionar `<link rel="preload" href="assets/hero-bg.mp4" as="video" type="video/mp4" />`
no head. No `aria-label` do h1 não mexer. Header sticky permanece (branco).

### Task S2.4 — JS: reduced-motion + parallax

Append em `site/landing.js` (dentro da IIFE existente, após o bloco reveal):

```js
  // V2: video de fundo — respeitar reduced-motion + parallax leve
  var bg = document.querySelector('.hero-bg');
  var bgVideo = bg ? bg.querySelector('video') : null;
  if (bgVideo && reduce) {
    bgVideo.pause();
    bgVideo.removeAttribute('autoplay');
    bgVideo.setAttribute('poster', 'assets/hero-bg.jpg');
    bgVideo.removeAttribute('src');
    bgVideo.load(); // libera banda; poster assume
  } else if (bgVideo && !window.matchMedia('(pointer: coarse)').matches) {
    // parallax: camada de fundo anda 25% da velocidade do scroll (so desktop)
    var ticking = false;
    window.addEventListener('scroll', function () {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(function () {
        var y = Math.min(window.scrollY, window.innerHeight);
        bg.style.transform = 'translateY(' + (y * 0.25) + 'px)';
        ticking = false;
      });
    }, {passive: true});
  }
```

### Task S2.5 — GREEN + deploy

```bash
cd /i/autojob/autojob-ext/site/test && node --test landing.test.mjs
# Expected: 13 pass, 0 fail
grep -c "hero-bg" ../index.html ../landing.css ../landing.js   # Expected: >=1 em cada
cd ../.. && git add -A && git commit -q -m "S2: landing v2 hero em camadas (video de fundo seamless + scrim + grid + parallax, copy RCD, demo vira secao) — 13/13 contratos"
git push origin master
sleep 90 && gh run list -L1   # Expected: Deploy landing success
```

## Phase S3 — Verificação final

```bash
curl -sk -o /dev/null -w "%{http_code} %{size_download}\n" --max-time 90 \
  https://matesu.me/autojob-ext/assets/hero-bg.mp4      # Expected: 200 < 6000000
curl -sk --max-time 60 https://matesu.me/autojob-ext/ | grep -c "hero-scrim"  # Expected: >=1
```

- QA visual no browser (se aprovação de remote-debugging for concedida):
  hero renderiza com vídeo em loop, texto legível (contraste), sticky-bar
  mobile não cobre conteúdo, scroll parallax suave, FAQ/âncoras ok,
  Lighthouse Performance ≥ 85 e A11y ≥ 95 (números no commit).
- Sem browser: vision_analyze dos frames do poster + HTTP checks acima.

## Tests / validation

| Gate | Comando | Esperado |
| --- | --- | --- |
| Contratos landing v2 | `cd site/test && node --test landing.test.mjs` | 13 pass |
| Chooser sem regressão | `cd extension/test && node --test chooser.test.mjs` | 5 pass |
| Vídeo no ar | `curl -sk -o /dev/null -w "%{size_download}" .../hero-bg.mp4` | 200, < 6 MB |
| Deploy | `gh run list -L1` | success |
| Página canônica | `curl -sk https://matesu.me/autojob-ext/ \| grep -c "baixar-cta"` | ≥ 2 |

## Risks / tradeoffs

- **Vídeo de fundo + texto = risco de contraste.** Mitigado por scrim .62 +
  teste de camada; validado com vision_analyze nos frames 0/120 (os piores
  momentos: tile grande / palavras claras atrás do texto).
- **Autoplay no mobile:** iOS só autoplaya com `muted playsinline` (presentes);
  parallax desabilitado em `pointer: coarse` para não gastar battery/CPU.
- **Bandwidth:** hero-bg < 4 MB + poster — comparável a uma foto grande;
  acceptable trade do pedido explícito do usuário. Se um dia pesar, migrar
  para poster animado (CSS) — anotar no brief.
- **`removeAttribute('src')` em reduced-motion** troca vídeo por poster
  estático — decisão RCD (default protege o usuário vulnerável a movimento).
- Skills vendorizados ficam fora do commit; o artefato versionado é só o
  `DESIGN-BRIEF.md` com crédito de proveniência (requisito da licença RCD).
- O teste V2 da ordem das camadas é frágil a reformatação de CSS; é de
  propósito — documenta a pilha. Aceitável.

## Open questions

1. Nome final: mantemos `matesu.me/autojob-ext` até decidir renomear o repo
   (`matesu.me/resume`) — muda o preload/poster? Não; nada muda no site.
2. Após a v2: quer o mesmo tratamento de camadas para a seção final
   ("Pare de reescrever currículo") com o vídeo espelhado? (YAGNI por ora.)
3. Adicionar trilha/som no vídeo? Não (muted por política de autoplay e
   bom-senso).
