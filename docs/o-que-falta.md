# O que falta

Lista viva do que ainda não existe, por fase. Atualizada a cada entrega.

**Situação em 19/08/2026:** 155 testes passando, ruff limpo, migração
inicial conferida em SQL. O que está pronto roda; o que falta está aqui.

## Resumo por fase

| Fase | Situação |
|---|---|
| 0 — Segurança do estado atual | ✅ concluída |
| 1 — Separação do front-end | ✅ concluída |
| 2 — Backend, banco e autenticação | 🟡 núcleo pronto, falta rodar no PostgreSQL |
| 3 — Família, papéis e permissões | 🟡 tela básica (listar/cadastrar dependente) pronta; falta redefinir senha, desativar conta e geofences |
| 4 — Objetivos, ocorrências e sessões | 🟡 backend pronto, falta a tela |
| 5 — Dashboards, pontos e recompensas | 🟡 painel e prêmios prontos; falta a tela de Progresso |
| 6 — Tempo real (WebSocket) | ⬜ não começou |
| 7 — Deploy no EasyPanel | ⬜ não começou |
| 8 — APK básico com Capacitor | ⬜ não começou |
| 9 — Monitoramento Android | ⬜ não começou |
| 10 — Finalização | ⬜ não começou |

## Bloqueado por infraestrutura

Nada disso avança sem os itens P1–P3 de `pendencias.md`.

- [ ] Rodar `alembic upgrade head` num PostgreSQL de verdade
- [ ] Refazer os testes contra PostgreSQL: enums nativos recusando valor
      inválido, índices parciais, `INET`, `JSONB` e concorrência — o
      SQLite dos testes não cobre nada disso
- [ ] Redis para Pub/Sub, presença e limite de tentativas

## Fase 2 — o que falta no backend

- [ ] Recuperação de senha real (token de uso único com expiração).
      Hoje o fluxo existe só no front-end antigo, sem servidor
- [ ] Limite de tentativas de login (a especificação pede, e sem Redis
      não dá para fazer direito entre várias instâncias)
- [ ] Registro de auditoria sendo gravado de fato. A tabela existe e
      está modelada, mas nenhum serviço escreve nela ainda —
      **importante**: o acesso do responsável às capturas precisa ficar
      registrado antes da Fase 9
- [ ] Endpoints de dispositivos (`/devices`): cadastrar, listar, revogar
- [ ] CRUD de matérias (`/subjects`) — hoje só dá para criar por SQL
- [ ] Importação do `localStorage` legado (seção 18), com o cuidado de
      **nunca** importar a senha em texto puro
- [ ] `/health/ready` conferindo Redis e volume graváveis, não só o banco

## Fase 3 — o que falta

- [ ] Redefinir a senha de um dependente (o responsável pode trocar, mas
      nunca ver a atual)
- [ ] Desativar e reativar conta de dependente
- [ ] Locais conhecidos (`known_locations`): CRUD das geofences
- [ ] Configurações por dependente: intervalo de captura, exigência de
      localização, regras de pontuação

## Fase 4 — o que falta

- [ ] Aprovação de adiantamento quando `adiantamento_exige_aprovacao`
      está ligado. Hoje o campo existe e é respeitado no modelo, mas o
      fluxo de pedir/aprovar não foi construído
- [ ] Aprovação final de ocorrência (`exige_aprovacao_final`), mesma
      situação
- [ ] Duplicar objetivo (a especificação lista entre as ações)
- [ ] Pausar e reativar objetivo pela API
- [ ] Frequência personalizada além de dias da semana
- [ ] Job que roda a virada de período sozinho. Hoje a agenda é
      materializada quando alguém consulta; um usuário que não abre o
      app fica sem ocorrências geradas

## Fase 5 — o que falta

- [ ] Notificações sendo criadas de fato (a tabela existe, nada escreve)
- [ ] Filtros do histórico por matéria, tipo e período — hoje só pagina
- [ ] Loja de recompensas repetíveis. A especificação trata como
      evolução futura, então **não** deve entrar no MVP

## Fase 6 — tempo real

- [ ] Endpoint WebSocket autenticado, com canais por usuário e família
- [ ] Redis Pub/Sub para distribuir entre instâncias
- [ ] Emitir os 15 eventos da seção 14. Os de sessão já são **gravados**
      em `session_events`; falta publicá-los
- [ ] Presença e reconciliação ao reconectar

## Fase 7 — deploy

- [ ] `Dockerfile` do backend e do front-end
- [ ] `docker-compose.production.yml`
- [ ] `nginx.conf` servindo o front, com proxy para `/api` e `/ws`
- [ ] Domínio, HTTPS e DNS
- [ ] Backup automático com restauração testada de verdade
- [ ] Ao concluir: **tornar o repositório privado** (L1 em `pendencias.md`)

## Fases 8 e 9 — Android

Nada começou. A Fase 9 tem uma dependência que não é técnica: **conversar
sobre consentimento** antes de implementar captura de tela e localização
de um dependente (L2 em `pendencias.md`).

## Front-end — ligando na API

**As quatro telas do MVP (login/cadastro, Objetivos, Estudar, Home) já
falam com a API de verdade quando `VITE_API_URL` está configurado.**
Testado de ponta a ponta num navegador real, contra o backend rodando —
cadastro, criar/editar objetivo, abrir sessão de estudo com heartbeat,
pausar, encerrar, concluir manualmente, ver os gráficos da Home, sair e
entrar de novo (14 cenários em `frontend/testes-integracao.mjs`, mais os
22 do cliente puro). As 40 verificações de regressão em modo local
continuam passando sem alteração nenhuma — o modo local não foi tocado.

- [x] Cliente HTTP com refresh automático do token
- [x] Login/cadastro/sair pela API (cookie HttpOnly, token em memória)
- [x] Sessão silenciosa na partida (retoma pelo cookie, sem novo login)
- [x] CRUD de objetivos pela API
- [x] Execução (tela Estudar) e conclusão de ocorrências pela API
- [x] Cronômetro com sessão real no servidor (abrir/heartbeat/pausar/
      retomar/finalizar) — a contagem visual continua local e instantânea;
      quem credita o tempo é o servidor
- [x] Painel (Home) com pontos, sequência e gráficos vindos da API

O que essa entrega **não fez**, de propósito, por não ter onde plugar
ainda (endpoint inexistente no backend):

- [ ] Editar perfil (nome/e-mail/senha) — mostra "em construção"
- [ ] Recuperar senha por e-mail — mostra "em construção", orienta a
      falar com o responsável
- [ ] Carregar dados de exemplo / apagar conta — desativados no modo
      online, com aviso explicando o motivo
- [ ] CRUD de matéria — todo objetivo aparece com a categoria "Sem
      matéria" (a API já tem `materia_id`, falta a tela)
- [ ] Configurar pontos fixos de tarefa no formulário — hoje todo
      objetivo tipo "tarefa" recebe 5 pontos fixos por padrão
- [ ] Configurar adiantamento (`permite_adiantar` etc.) no formulário —
      hoje todo objetivo nasce sem permissão de adiantar
- [x] Tela Família (responsável) — lista os dependentes com resumo
      (minutos hoje, concluídos hoje, pontos, sequência de dias) e
      cadastra um novo dependente (`POST /auth/dependentes`)
- [x] Menu por papel — o dependente não vê mais as abas Objetivos nem
      Família (antes a API já bloqueava com 403, só a interface não
      escondia os botões); modo local continua com as 4 abas de sempre
- [x] Tela Prêmios (trilhas de recompensa) — cada pessoa vê o progresso
      das próprias trilhas (pontos, barra até o próximo nível, prêmio),
      solicita o que desbloqueou e o responsável confirma a entrega; o
      responsável ainda cria a trilha (só no escopo "todos os pontos" —
      matéria/objetivo específico segue de fora, ver `CRUD de matéria`
      abaixo) e adiciona níveis, e pode trocar de beneficiário (si
      mesmo ou um dependente) para gerenciar as trilhas de cada um
- [ ] Tela Progresso (dependente acompanhar o próprio
      histórico/sequência em mais detalhe) — endpoint pronto
      (`GET /historico`), tela não construída ainda
- [ ] Estado de "carregando" explícito — hoje uma tela online demora
      exatamente o tempo do fetch antes de aparecer; sem esqueleto/spinner

O modo é escolhido por `VITE_API_URL` no build: vazio = local (o que o
Pages publica hoje), preenchido = API.

## Dívidas conhecidas

- [ ] `E` no front-end ainda é objeto mutável compartilhado (D6)
- [ ] Teto de acúmulo (6× diário, 3× nos demais) escolhido sem medição (L4)
- [ ] Sem CI: os testes rodam só na minha mão, não a cada push
- [ ] Sem `docker-compose.dev.yml` para subir tudo local com um comando
