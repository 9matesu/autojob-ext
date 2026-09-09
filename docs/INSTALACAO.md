# resuMe — Instalação (usuário final)

## Opção A — Pacote portável (recomendado)

Baixe `resuMe-1.0.0-windows-x64.zip` na página de
[releases](https://github.com/9matesu/autojob-ext/releases). Ele contém tudo:
extensão, motor local com Python embutido e compilador LaTeX — sem instalador,
sem pip, sem PATH.

1. **Descompacte em local fixo** (ex.: `C:\resuMe`). O native host grava
   caminhos absolutos — se você mover a pasta depois, rode o passo 3 de novo.
2. **Extensão**: abra `chrome://extensions` → ative **Modo do desenvolvedor**
   (canto superior direito) → **Carregar sem compactação** → selecione a pasta
   `extension\`.
3. **Motor liga sozinho (recomendado)**: abra um PowerShell e rode
   `powershell -ExecutionPolicy Bypass -File .\native-host\install-host.ps1`.
   A partir daí, abrir o painel lateral inicia o motor automaticamente.
   - Alternativa manual: execute `start-engine.ps1` antes de usar.
4. **Primeiro uso**: clique no ícone resuMe → envie seu currículo base (PDF,
   DOCX, TXT ou `.tex`) → configure o provedor de IA → capture sua primeira
   vaga (`Alt+Shift+A` na aba da vaga).

### Windows SmartScreen

O zip e o `ResumeHost.exe` não são assinados digitalmente. Se o SmartScreen
avisar: botão direito → Propriedades → **Desbloquear**, ou
"Mais informações → Executar assim mesmo" no aviso. É esperado para software
distribuído sem certificado pago.

### Antivírus

Compiladores LaTeX escrevem muitos arquivos temporários; alguns antivírus
(Pandas/AVG/McAfee) podem atrasar a primeira compilação. Se a compilação
falhar na primeira tentativa, tente de novo — o backend já faz um retry
automático. Adicionar a pasta `C:\resuMe` às exclusões resolve definitivamente.

### Atualizar de uma versão 0.x (AutoJob Studio)

- Desinstale a extensão antiga em `chrome://extensions` e carregue a nova
  (a ID é a mesma; nenhuma configuração é perdida).
- Reexecute o `install-host.ps1` — o native host foi renomeado de
  `com.autojob.host` para `com.resume.host`.
- O banco antigo (`autojob.db`) é migrado manualmente só se você quiser:
  feche o motor e renomeie `backend\data\autojob.db` → `resume.db`.

## Opção B — Desenvolvedor (código-fonte)

Veja [EXTENSAO.md](EXTENSAO.md) → seção "Instalação".
