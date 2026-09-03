# Template Standard ATS ("editorial")

Layout editorial limpo de alta compatibilidade ATS, bilíngue PT/EN automático.

- `lang = "pt"` (padrão) → `\usepackage[portuguese]{babel}`, seções em português
  (Resumo Profissional, Experiência Profissional, Formação Acadêmica, Projetos, Competências Técnicas, ...).
- `lang = "en"` → `\usepackage[english]{babel}`, seções em inglês.

A escolha do idioma é feita pelo pipeline a partir do idioma detectado na
descrição da vaga (português por padrão; inglês quando a vaga claramente pede).
