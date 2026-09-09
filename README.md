# resuMe

Adapta seu currículo em LaTeX para qualquer vaga, direto do navegador.
O detector lê o **DOM do painel da vaga que você clicou** (sem screenshot),
envia o texto ao motor local, que extrai os dados com IA, customiza o
**currículo base do onboarding**, compila o PDF em LaTeX e registra no histórico.

**Download para usuários**: [página do resuMe](https://matesu.me/autojob-ext)
→ botão "Baixar para Windows" (`resuMe-1.0.0-windows-x64.zip`, portável:
extensão + motor + Python embutido + Tectonic). Instruções em
[docs/INSTALACAO.md](docs/INSTALACAO.md).

Documentação (arquitetura, fluxo, permissões, troubleshooting):
**[docs/EXTENSAO.md](docs/EXTENSAO.md)** · Privacidade:
**[docs/PRIVACIDADE.md](docs/PRIVACIDADE.md)**.

## Setup rápido (dev)

```powershell
# 1. Motor local (venv + deps na primeira vez)
.\start-backend.ps1

# 2. Interface da extensão
cd ui
npm install
npm run build

# 3. Chrome: chrome://extensions → "Modo do desenvolvedor" →
#    "Carregar sem compactação" → pasta extension/

# 4. (opcional) Backend inicia sozinho ao abrir o painel lateral
cd ..
.\native-host\install-host.ps1
```

## Uso

Abra uma vaga (LinkedIn, Gupy, Indeed, Greenhouse...) → clique no ícone da
extensão → **Capturar Vaga** → o painel candidato fica destacado em amarelo;
**clique** para abrir a prévia — **edite o texto ali se precisar** — e
`CAPTURAR`. Um único `Esc` sai da captura a qualquer momento.
O resultado traz o match honesto e as palavras-chave aplicadas — baixe o PDF
ou refine no Estúdio. `Alt+Shift+A` captura direto da aba ativa.

## Package de release

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\package-release.ps1
# -> dist\resuMe-<versão>-windows-x64.zip
```

## Estrutura

- `extension/` — extensão MV3 (manifest, background, content script + páginas buildadas)
- `ui/` — React + Tailwind (painel lateral e aba do Estúdio); fontes OFL em `public/fonts/`
- `backend/` — FastAPI: IA, importação de currículo, Tectonic/LaTeX, SQLite
- `native-host/` — auto-start do backend via native messaging
- `site/` — página de download estática (GitHub Pages)
- `scripts/` — empacotamento do release portável

## Identidade visual

Duas famílias tipográficas e ponto: **Instrument Serif** (títulos editoriais)
e **Schibsted Grotesk** (tudo funcional) — ambas OFL, embutidas como woff2
(`ui/public/fonts/`), zero CDN na extensão. O logo é o monograma geométrico
"**Me**" (M monolinear de ápice em esquadro + "e" de um andar) sobre preto,
traço amarelo — modernismo suíço, duas cores, sem gradientes.
No site, Schibsted é substituído por Switzer (visualmente gêmeo) via CDN da
Fontshare — permitido no site próprio; a ITF-FFL não permite redistribuí-lo no zip.
