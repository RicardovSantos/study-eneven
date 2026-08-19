# Pendências e decisões

> Para a lista do que **ainda não foi construído**, por fase, veja
> [`o-que-falta.md`](o-que-falta.md). Este arquivo cuida do que está
> travado esperando alguém, e das decisões já tomadas.

Lista viva do que está travado, esperando alguém ou já decidido. Atualizar
a cada fase.

## Esperando ação do Ricardo

| # | O que | Bloqueia | Situação |
|---|---|---|---|
| P1 | String interna de conexão do PostgreSQL do EasyPanel | Rodar as migrações e subir a API de verdade | **Aberto** |
| P2 | Criar o subdomínio `devlog.eneven.com.br` (registro `A` para o IPv4 da VPS) | Fase 7 | **Aberto** |
| P3 | Criar os serviços `devlog-postgres` e `devlog-redis` no EasyPanel | Fase 7 | **Aberto** |

> **Segredos nunca passam por chat, commit ou issue.** Cadastrar direto no
> painel do EasyPanel. O código lê tudo de variável de ambiente, e o
> `.env.example` fica sem nenhum valor real.

## Lembretes com data marcada

| # | Lembrete | Quando |
|---|---|---|
| L1 | **Tornar o repositório privado.** Hoje é público, e a especificação com arquitetura, modelo de dados e estratégia de monitoramento está versionada aqui. O Pages em repositório privado exige plano pago, por isso a troca espera o site mudar para o domínio próprio. | Ao concluir a Fase 7 |
| L2 | **Conversar sobre consentimento antes de implementar monitoramento.** Captura de tela e localização de um dependente têm exigência legal (LGPD) e não se resolvem só com código. Mesmo com tudo transparente como a especificação pede, o dependente precisa saber e concordar. | Antes da Fase 9 |
| L3 | **Descartar a senha legada em texto puro.** O `localStorage` guarda a senha sem hash. Na importação (seção 18), migrar objetivos e histórico, nunca a senha — exigir senha nova. | Fase 2 |
| L4 | **Rever o teto de acúmulo com dados reais.** Hoje é 6× a meta em objetivos diários e 3× nos demais, escolhido sem medição. | Depois de algumas semanas de uso |

## Decidido

| # | Decisão | Motivo |
|---|---|---|
| D1 | Repositório segue **público** até a Fase 7 | Pages gratuito só em repositório público; quando o site migrar para o domínio próprio, o Pages deixa de importar |
| D2 | Publicação por **GitHub Actions** | O site passou a exigir build; confirmado funcionando em 19/08 |
| D3 | **Sem Chart.js** | Os gráficos em SVG puro têm 43 linhas e cobrem os dois casos; a seção 5.1 permite preservá-los |
| D4 | **Vanilla JS, sem framework** | Exigência da seção 5.1 para a primeira evolução |
| D5 | Ponto de restauração em **branch**, não tag | O proxy da sessão bloqueia push de tags (HTTP 403) |
| D6 | `E` continua objeto mutável compartilhado | Trocar por store imutável junto com a API, na Fase 2; separar as mudanças para saber o que quebrou o quê |

## Limitações conhecidas do ambiente

- **Push de tags bloqueado** (HTTP 403 no proxy). Pontos de restauração
  viram branches `backup/*`.
- **Sem acesso de rede a `github.io`** a partir desta sessão: não dá para
  conferir o site publicado por aqui. A verificação é feita pelo status do
  workflow e por testes locais no build.
- **Sem servidor PostgreSQL** na sessão, só o cliente `psql`. Contornado
  em dois níveis: o DDL do dialeto PostgreSQL é gerado e conferido sem
  banco vivo (`alembic upgrade head --sql`), e a suíte de testes roda
  contra SQLite em memória, graças aos tipos com variante em
  `app/db/tipos.py`.

  **O que isso não cobre** e precisa ser refeito contra o PostgreSQL de
  verdade quando P1 for resolvido: enums nativos recusando valor
  inválido, índices parciais, `INET`, `JSONB` com operadores próprios e
  o comportamento sob concorrência.
