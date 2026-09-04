# AutoJob Studio — Extensão Chrome

Documentação da extensão, do motor local e do fluxo ponta-a-ponta.

## O que é

Extensão Chrome (Manifest V3) que adapta o **currículo base enviado no onboarding**
para cada vaga. A captura lê o **DOM da página** — sem screenshot, sem visão
computacional, sem janelas separadas. O resultado é um currículo LaTeX compilado
para PDF, pronto para ATS.

O que **não** é: não gera carta de apresentação nem mensagem para recrutador.
O entregável é sempre o currículo customizado.

## Arquitetura

```
┌────────────────────────── Chrome ──────────────────────────┐
│                                                            │
│  Página da vaga                Painel lateral (sidepanel)  │
│  ┌────────────────┐            ┌────────────────────────┐  │
│  │ content.js     │◄─mensagens─│ ui/ (React)            │  │
│  │ detector de    │            │ captura · histórico ·  │  │
│  │ painel DOM     │            │ estúdio · config       │  │
│  └───────┬────────┘            └───────────┬────────────┘  │
│          │                                 │               │
└──────────┼─────────────────────────────────┼───────────────┘
           │  POST /api/adapt-text           │ HTTP
           ▼                                 ▼
┌──────────────────── FastAPI sidecar (porta 8322) ──────────┐
│ extração da vaga (LLM texto→JSON) → adaptação sobre o      │
│ perfil mestre → template LaTeX → Tectonic → PDF → SQLite   │
│                                                            │
│ native messaging host (AutoJobHost.exe) sobe o motor       │
│ automaticamente quando o painel abre                       │
└────────────────────────────────────────────────────────────┘
```

- `extension/` — extensão carregável (manifest, background, content script +
  páginas compiladas do `ui/`).
- `ui/` — app React (Vite + Tailwind) que gera `sidepanel.html` e `studio.html`.
- `backend/` — motor FastAPI local: IA, importação de currículo, compilação
  LaTeX (Tectonic), histórico SQLite.
- `native-host/` — host de native messaging que inicia o backend ao abrir o painel.

## Fluxo ponta-a-ponta

1. **Onboarding (primeira execução)** — você envia o currículo base
   (PDF/DOCX/TXT/MD/TeX). O backend extrai o texto e estrutura um
   **perfil mestre** (dados pessoais, resumo, experiências, liderança,
   formação, habilidades, projetos, idiomas com nível, certificações).
   Uploads `.tex` são lidos direto da estrutura (`\section`, `\cventry`,
   `\item`); PDF achata para o parser por blocos (linhas de cabeçalho +
   bullets, com junção de quebras de linha do PDF). Você revisa e confirma
   cada seção no passo 2 e configura a IA no passo 3. O perfil mestre fica
   no SQLite local e é a **única fonte de fatos** para todas as adaptações.
   Para trocar o currículo: Config → "Trocar currículo base".
2. **Captura (modo inspetor)** — na página da vaga, clique em "Capturar Vaga"
   no painel ou `Alt+Shift+A`. O content script entra em **modo de seleção**:
   o mouse destaca exatamente o elemento sob o cursor (outline amarelo), o
   selo mostra o breadcrumb real (`body > main > article.job-posting`) e a
   contagem de chars. `↑`/`↓` navegam pai/filho na árvore. Na entrada, o
   maior bloco de texto visível já vem destacado como ponto de partida
   (dinâmico, sem listas). Um clique (ou Enter) abre o **toast de prévia**
   com o texto exato do elemento + `CAPTURAR` / `ESCOLHER OUTRO`. O que
   aparece no toast é byte a byte o que vai ao backend — sem parser,
   sem poda, sem heurística no caminho.
3. **Extração da vaga** — o texto do elemento vai para `POST /api/adapt-text`.
   O LLM devolve JSON estruturado (título, empresa, local, requisitos,
   keywords) usando **só a vaga principal** (cursos/promos/vagas relacionadas
   são ignorados por instrução explícita) e sem inventar nada. A resposta
   traz `captured_chars`, exibido no card do painel.
4. **Adaptação** — o LLM recebe o perfil mestre + a vaga e devolve o
   currículo customizado: resumo reescrito para o papel, habilidades e
   experiências reordenadas/reescritas (**mesmos fatos, outra ênfase**),
   projetos reordenados, `match_score` honesto 0–100 e `applied_keywords`
   (apenas keywords da vaga que o candidato realmente possui). Regras
   rígidas no system prompt: dados da vaga são cercados por fence e nunca
   são instruções; proibido inventar empresas, datas, métricas ou skills.
5. **Compilação** — o perfil adaptado renderiza o template `editorial`
   (LaTeX ATS-standard, PT/EN automático) e o Tectonic compila o PDF.
6. **Histórico** — job + PDF + perfil adaptado ficam no SQLite; o painel
   "Arquivo" lista tudo para rebaixar.

## Instalação

1. **Backend**: `.\start-backend.ps1` (cria venv e instala deps na primeira vez;
   requer Python 3.11+). Ou deixe o auto-start cuidar disso (passo 4).
2. **UI**: `cd ui && npm install && npm run build` — gera as páginas dentro de
   `extension/`.
3. **Extensão**: `chrome://extensions` → ativar "Modo do desenvolvedor" →
   "Carregar sem compactação" → selecionar `extension/`. A ID é fixa
   (`mkopnnfghehbonobjfjmifddejbjfdea`) porque o manifest traz uma `key` pinada.
4. **Auto-start do motor (opcional, recomendado)**:
   `.\native-host\install-host.ps1` — compila `AutoJobHost.exe` (PyInstaller),
   grava a config de máquina (`autojob-host.json`), o manifest do host
   (`com.autojob.host.json`) e registra em
   `HKCU\Software\Google\Chrome\NativeMessagingHosts\com.autojob.host`.
   Depois disso, abrir o painel com o motor desligado dispara o start
   automático (log em `backend/data/autojob-backend.log`).

## Uso diário

| Ação | Como |
| --- | --- |
| Capturar vaga | Painel → "Capturar Vaga" → clique no painel → confira a prévia → `CAPTURAR` (ou `Alt+Shift+A`) |
| Escolher outro painel | botão `ESCOLHER OUTRO` no toast (volta à seleção) |
| Cancelar seleção | `Esc` no toast volta à seleção; `Esc` na seleção cancela |
| Editar antes de baixar | Resultado → "Abrir Estúdio" (aba: editor Visual/LaTeX + preview PDF + recompilar) |
| Versões anteriores | Painel → "Arquivo" → Baixar PDF |
| Trocar IA/chave/modelo | Painel → "Config" |

## Permissões (e por quê)

| Permissão | Uso |
| --- | --- |
| `sidePanel` | UI principal dockada ao navegador |
| `storage` | passar o resultado da captura para a aba do Estúdio |
| `tabs` | localizar a aba ativa para enviar a mensagem de captura |
| content script `<all_urls>` | o detector precisa rodar na página da vaga |
| host `http://127.0.0.1:8322/*` | comunicação com o motor local |

Sem `activeTab`/`<all_urls>` em `host_permissions`: nada de acesso a dados de
navegação; o único conteúdo lido é o texto do painel que **você** clicou.

## Dados e privacidade

- Perfil mestre, API key e histórico: apenas no SQLite local (`backend/data/`).
- O texto do painel clicado e o perfil vão para o provedor de IA configurado
  (Gemini/OpenAI/OpenRouter/Ollama local). Sem chave de API, o backend
  retorna erro explícito em vez de qualquer conteúdo — não existe dado
  fabricado em nenhum caminho. Nada é enviado a servidores do AutoJob —
  não existem.
- O PDF é gerado localmente pelo Tectonic.

## Troubleshooting

| Sintoma | Causa/Solução |
| --- | --- |
| "Recarregue a página da vaga (F5)" | content script não injetado (aba aberta antes de instalar/recarregar a extensão) |
| "Service worker registration failed. Status code: 2" | registro obsoleto do SW no perfil do Chrome (comum após muitos ↻ com key pinada): remova o cartão da extensão, feche o Chrome com `chrome://restart`, carregue de novo |
| Seleção não inicia | página exige rolagem prévia ou a vaga está em iframe cross-origin (limitação conhecida) |
| Elemento errado destacado | o outline mira o elemento exato sob o cursor; use ↑/↓ para ajustar pai/filho |
| Texto com assunto estranho (ex.: curso aleatório) | você clicou no elemento errado — o toast mostra exatamente o que será enviado; cancele e clique no painel certo |
| Dados parecem falsos (nome/empresa que não são seus) | confira em Config → "Currículo base" qual perfil está ativo; se for resto de teste, use "Trocar currículo base" e refaça o onboarding com seu currículo real |
| Onboarding não aparece | ele só aparece sem perfil ativo; para refazer, Config → "Trocar currículo base" |
| Estúdio mostra "Resultado expirado" | o registro sumiu do histórico (limpeza) — capture a vaga novamente no painel |
| Pré-visualização do PDF falha | confira se o motor está rodando; use "Tentar novamente" ou "Baixar PDF" na própria tela |
| "Motor Offline" persistente | rode `.\start-backend.ps1`; confira `backend/data/autojob-backend.log`; reinstale o host se o auto-start falhar |
| Match aparece como "—" | o provedor não devolveu `match_score`; o valor nunca é inventado |
| Porta 8322 ocupada por outro processo | encerre-o ou ajuste `port` em `native-host/autojob-host.json` e `ui/src/chrome.ts` |

## Desenvolvimento

```powershell
cd ui
npm run dev        # http://localhost:5173/sidepanel.html (chrome.* desabilitado fora da extensão)
npm run build      # compila para extension/
npm run lint       # oxlint
```

```powershell
cd backend
.venv\Scripts\python -m pytest tests -q
```

Os testes rodam num banco SQLite temporário (`AUTOJOB_DATA_DIR` apontado por
`tests/conftest.py`) — nunca tocam `backend/data/autojob.db`.

Fixturas de seleção ficam em `extension/test/fixtures/` (LinkedIn/Indeed/Gupy-like).
`extension/test/build_shim.py` gera o `content_shim.js` que permite dirigir o
`content.js` real pelo console: `__start` → mousemove/click/setas → toast →
`CAPTURAR`/`ESCOLHER OUTRO`/Enter/Esc, com asserts de que o outline mira o
elemento exato e o texto postado é byte a byte o `innerText` dele.

Estrutura: `ui/src/chrome.ts` isola toda a API do Chrome com guards para o
app funcionar como página comum em dev. `extension/content.js` é estático
(não passa pelo build). Endpoints: `health`, `settings(+test)`, `profile`,
`parse-resume`, `adapt-text`, `compile`, `polish-bullet`, `history`,
`resumes/{id}/pdf`.
