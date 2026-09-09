# resuMe — Chrome Extension

Adapta seu currículo em LaTeX para qualquer vaga, direto do navegador.
O detector lê o **DOM do painel da vaga que você clicou** (sem screenshot),
envia o texto ao motor local, que extrai os dados com IA, customiza o
**currículo base do onboarding**, compila o PDF em LaTeX e registra no histórico.

Documentação completa (arquitetura, fluxo, permissões, troubleshooting):
**[docs/EXTENSAO.md](docs/EXTENSAO.md)**.

## Setup rápido

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
**clique** para capturar exatamente aquele elemento (`Esc` cancela).
O resultado traz o match honesto e as palavras-chave aplicadas — baixe o PDF
ou refine no Estúdio. `Alt+Shift+A` captura direto da aba ativa.

## Estrutura

- `extension/` — extensão MV3 (manifest, background, content script + páginas buildadas)
- `ui/` — React + Tailwind (painel lateral e aba do Estúdio)
- `backend/` — FastAPI: IA, importação de currículo, Tectonic/LaTeX, SQLite
- `native-host/` — auto-start do backend via native messaging
