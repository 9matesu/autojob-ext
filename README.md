# AutoJob Studio — Chrome Extension

Adapta seu currículo em LaTeX para qualquer vaga, direto do navegador.
O detector de painel lê o DOM da página da vaga (sem screenshot), envia o texto
para o motor local, que extrai os dados com IA, adapta seu perfil mestre,
compila o PDF em LaTeX e registra no histórico.

## Arquitetura

- `extension/` — extensão Chrome (Manifest V3): painel lateral + content script detector.
- `ui/` — app React (Vite + Tailwind) que compila para `extension/` (sidepanel.html, studio.html).
- `backend/` — motor FastAPI local: IA (Gemini/OpenAI/OpenRouter/Ollama/Mock), importação de
  currículo (PDF/DOCX/TXT/MD/TeX), compilação LaTeX (Tectonic), histórico SQLite.

## Executar

1. Backend (uma vez, ou sempre que quiser):
   ```powershell
   .\start-backend.ps1
   ```
   (cria o venv na primeira execução; requer Python 3.11+)
2. UI:
   ```powershell
   cd ui
   npm install
   npm run build
   ```
3. Chrome: `chrome://extensions` → ativar "Modo do desenvolvedor" →
   "Carregar sem compactação" → selecionar a pasta `extension/`.
4. Auto-start do backend ao abrir o painel (uma vez):
   ```powershell
   .\native-host\install-host.ps1
   ```
   Compila o host de native messaging (`AutoJobHost.exe`), registra-o no
   registro do usuário e vincula à ID fixa da extensão. Depois disso, abrir o
   painel lateral inicia o motor automaticamente se a porta 8322 estiver livre.
5. Clique no ícone da extensão para abrir o painel lateral.

## Uso

- Abra uma vaga (LinkedIn, Gupy, Indeed, Greenhouse...) e clique em
  **Capturar Vaga** no painel lateral ou pressione `Alt+Shift+A`.
- O AutoJob destaca o painel detectado em amarelo, extrai o texto do DOM,
  adapta o currículo e mostra o resultado (match, pitch, PDF).
- **Abrir Estúdio** edita os bullets, o código LaTeX e recompila o PDF em uma aba.
- **Arquivo** lista todas as adaptações; **Config** troca provedor/modelo/chave de IA.
- **Capturar Tela Visível** é o fallback por visão computacional quando o DOM da
  página não expõe a vaga (ex.: canvas, imagens).

## Onboarding

Na primeira execução, o painel pede o currículo base (arraste PDF/DOCX/TXT/MD/TeX),
mostra o perfil mestre extraído para revisão e configura a IA.

## Desenvolvimento

```powershell
cd ui
npm run dev      # http://localhost:5173/sidepanel.html (chrome.* desabilitado fora da extensão)
npm run build    # gera extension/sidepanel.html, studio.html e assets/
npm run lint     # oxlint
```

```powershell
cd backend
.venv\Scripts\python -m pytest tests -q
```
