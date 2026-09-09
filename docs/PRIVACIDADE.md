# resuMe — Privacidade

Princípio: **nada sai da sua máquina, exceto o que a IA que você escolheu
precisa ler.** Não existem servidores do resuMe.

## O que fica local

| Dado | Onde |
| --- | --- |
| Currículo base / perfil mestre | SQLite local (`backend\data\resume.db`) |
| Chave de API do provedor de IA | mesma base, lida só pelo motor local; o navegador nunca vê a chave |
| Vagas capturadas + PDFs + histórico | `backend\data\` |
| Preferências (template, idioma) | `backend\data\resume.db` |

O painel lateral conversa apenas com `http://127.0.0.1:8322` (host
permission única do manifest). As permissões da extensão estão documentadas
em [EXTENSAO.md](EXTENSAO.md#permissões-e-por-quê).

## O que é enviado (e para onde)

1. **Texto do painel da vaga que VOCÊ clicou** + seu perfil mestre →
   provedor de IA configurado em Config (Gemini, OpenAI, Anthropic, Groq,
   OpenRouter, Mistral, DeepSeek, xAI, NVIDIA, Together — ou **Ollama
   local**, que zera o tráfego externo).
2. Nada mais. Sem telemetria, sem analytics, sem "verificar atualização" —
   o site de download é estático e a extensão não o consulta.

## Captura

- A captura lê **texto do DOM** do elemento selecionado — sem screenshot da
  página, sem visão computacional por padrão.
- O modo inspetor só roda enquanto ativo: sem `Esc`/captura, não captura;
  sem ele ativado, o content script fica inerte (só escuta mensagens).
- O textarea da prévia mostra exatamente o texto que será enviado; edite antes
  de confirmar se a página contiver dados que você não quer mandar.
- Limite duro de 30.000 caracteres no envio de texto bruto.

## Fontes e terceiros

- A **extensão** embute apenas fontes sob licença SIL OFL (Instrument Serif,
  Schibsted Grotesk) — zero requisições a CDNs.
- O **site** resuMe carrega Switzer via CDN da Fontshare (permitido pela
  ITF-FFL para o próprio site); é a única requisição de terceiros da página,
  feita pelo navegador de quem a visita, não pela extensão.

## Compilação

PDFs são gerados localmente pelo Tectonic (embutido no pacote portável).
Em nenhum momento seu currículo é enviado a um serviço de renderização.

## Desinstalação

Remover a extensão em `chrome://extensions`, apagar a chave registrada em
`HKCU\Software\Google\Chrome\NativeMessagingHosts\com.resume.host` e deletar
a pasta do produto apaga 100% dos dados.
