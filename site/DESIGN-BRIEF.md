# resuMe Landing v2 — Design Brief

Destilacao dos skills [`revenue-centric-design`](https://github.com/heliocosta-dev/revenue-centric-design)
(licenca: attribution required, sem uso em gambling) e
[`ui-ux-pro-max`](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
(MIT), aplicados a `site/index.html`. Este arquivo documenta DECISOES; o
codigo e a fonte de verdade.

## Principio -> decisao nesta pagina

| Principio (fonte) | Decisao v2 |
| --- | --- |
| 5-second test: o que isso? para quem? por que agora? (RCD 2026-05-29) | H1 diz O QUE faz + PARA QUEM ("Cada vaga pede um currículo diferente") e o sub fecha o ICP ("para quem aplica para vagas online e está cansado..."). |
| Dor antes da feature (RCD 2026-05-01) | Primeiro verso do h1 = dor do visitante; segundo = resultado do produto. Nenhum jargao (LaTeX aparece so como meio). |
| CTA microcopy, nao cor (RCD 2026-05-25): o que acontece, quanto tempo, o que custa | Botao: "Baixar grátis — instala em 2 minutos" (custo: gratis; tempo: 2 min; acao: baixar). |
| Click trigger sob o CTA (RCD 2025-12-19) | Linha `.cta-note` = quebra de objecoes tecnicas: "Windows 10/11 · Google Chrome · roda offline". |
| Value first, ask later / prova >= promessa (RCD 2025-11-10) | Demo em video (secao #demo) chega ANTES dos steps e do pricing-free badge some para badge simples — a promise tangivel (mock do fluxo real) vem no primeiro scroll. |
| Primary action vence num glance; um CTA dominante (RCD 2026-04-08) | No hero: amarelo solido = unico CTA cheio; o secundario e ghost/branco. `#demo` ghost nao compete (fundo transparente, borda branca). |
| Checklist 2026: Hero->Pain->Solution->Proof->CTA, CTA a cada ~1.5 secoes | Ordem: hero(dor+CTA) > marquee(promise) > demo(proof visual) > como funciona(solution) > cards(features skim) > pull(autoria) > privacia(proof racional) > FAQ(objecoes) > CTA final. |
| Sem prova inventada (hard rule do usuario + RCD 4.2-4.5 stars: unanimidade = fake) | `TODO-PROVA-SOCIAL` permanece vazio — bloqueado por teste. Credibilidade por precisao factual ("11 provedores", "30 segundos"), nao por depoimentos fabricados. |
| Contraste pre-verbal antes da copia (RCD 2026-04-28; PRO-MAX: >=4.5:1 texto normal em dark) | Fundo video escuro (#0A0A0A em media) + scrim rgba(0,0,0,.62) => branco (#fff) ~13:1, sub #cfcfcf ~9:1, meta #9a9a9a ~5.3:1. NENHUM texto funcional abaixo de 4.5:1. |
| Light/dark parity (PRO-MAX) | Estados dos botoes no hero (ghost hover = branco solido/preto) definidos explicitamente, sem assumir herdanga do light mode. |
| Reduced motion sem quebrar layout (PRO-MAX) | `landing.js` pausa e DRENA o video de fundo (poster assume) com `prefers-reduced-motion: reduce`; `.reveal` ja e neutro nesse modo; parallax so em desktop pointer:fine. |
| Stable interaction states (PRO-MAX) | Micro-interacoes existentes (shadow-shift nos botoes) ja traduzem sem reflow; parallax e translate na camada de fundo, nunca no texto. |
| Performance is conversion (RCD Vodafone: LCP) | hero-bg.mp4 budget < 4 MB, `preload="auto"` so no video de fundo, poster como fallback de LCP, demo.mp4 lazy por secao (abaixo do fold: `loading` de video nao existe — `preload="none"` e o equivalente correto, ver teste V2). |
| Loop sem emenda (PRO-MAX motion) | `ResumeHeroBg`: periodos = divisores exatos de 240 frames (grid 1 celula/loop, tile com wrap, pulso senoidal 1/loop). |
| Brand sacred (skill rcd-uiux-refactor do usuario) | Video de fundo todo em preto/amarelo da marca; zero gradiente colorido, zero blur; cantos retos no texto, tile arredondado = unico do logo. Hero dark = camada nova, nao reskin. |

## Contraste medido (WCAG, sobre o frame escuro medio do video)

- #FFFFFF / scrim(#000@.62 sobre #0A0A0A ≈ #121212): ~16.9:1
- #CFCFCF / mesma base: ~11.5:1
- #9A9A9A / mesma base: ~6.0:1
- Amarelo #FFE800 / preto: ~17.5:1

## Fontes de consulta

- `revenue-centric-design/references/conversion-and-landing-pages.md`
- `ui-ux-pro-max/.claude/skills/ui-ux-pro-max/references/pro-rules.md` (dark contrast, states, reduced-motion)
