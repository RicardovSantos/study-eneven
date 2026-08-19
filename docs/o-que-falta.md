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
| 3 — Família, papéis e permissões | 🟡 backend pronto, falta a tela |
| 4 — Objetivos, ocorrências e sessões | 🟡 backend pronto, falta a tela |
| 5 — Dashboards, pontos e recompensas | 🟡 backend pronto, falta a tela |
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

## Front-end — o buraco maior

O back-end das fases 2 a 5 está pronto e testado, mas **o front-end
continua falando com `localStorage`**. Nenhuma tela chama a API ainda.

- [ ] Cliente HTTP com refresh automático do token
- [ ] Trocar o login local pelo `/auth`
- [ ] Trocar o CRUD local pelo `/objetivos`
- [ ] Trocar o cronômetro local pelas `/sessoes` com heartbeat
- [ ] Ligar os painéis em `/dashboard`
- [ ] Telas novas: Família, Progresso, Recompensas
- [ ] Menu por papel (responsável e dependente veem coisas diferentes)
- [ ] Estados de carregando, erro e offline

Enquanto isso não for feito, o app publicado continua sendo o de arquivo
único com dados locais — que funciona, mas é de um usuário só, sem
servidor.

## Dívidas conhecidas

- [ ] `E` no front-end ainda é objeto mutável compartilhado (D6)
- [ ] Teto de acúmulo (6× diário, 3× nos demais) escolhido sem medição (L4)
- [ ] Sem CI: os testes rodam só na minha mão, não a cada push
- [ ] Sem `docker-compose.dev.yml` para subir tudo local com um comando
