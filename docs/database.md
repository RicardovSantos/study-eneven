# Modelo de dados

19 tabelas, criadas pela migração `0001_estrutura_inicial`. O SQL gerado
foi conferido em modo offline (`alembic upgrade head --sql`): 20 `CREATE
TABLE` (as 19 mais `alembic_version`), 14 tipos enum, 21 índices, 48
chaves estrangeiras e 24 restrições `CHECK`.

## Diagrama

```mermaid
erDiagram
    users ||--o{ family_members : "participa"
    families ||--o{ family_members : "reúne"
    users ||--o{ refresh_tokens : "autentica"
    users ||--o{ devices : "usa"
    families ||--o{ subjects : "organiza"
    families ||--o{ objectives : "contém"
    users ||--o{ objectives : "é titular"
    objectives ||--o{ objective_occurrences : "gera"
    objective_occurrences ||--o{ study_sessions : "é cumprida por"
    objectives ||--o{ study_sessions : "cronometra"
    study_sessions ||--o{ session_events : "registra"
    study_sessions ||--o{ screen_captures : "captura"
    study_sessions ||--o{ session_locations : "localiza"
    families ||--o{ known_locations : "define"
    known_locations ||--o{ session_locations : "identifica"
    users ||--o{ point_ledger : "acumula"
    objectives ||--o{ point_ledger : "credita"
    users ||--o{ reward_tracks : "beneficia"
    reward_tracks ||--o{ reward_levels : "escalona"
    reward_levels ||--o{ reward_unlocks : "desbloqueia"
    users ||--o{ notifications : "recebe"
    users ||--o{ audit_logs : "gera"
```

## Decisões que valem explicar

### Objetivo e ocorrência são coisas separadas

O MVP controlava recorrência com um contador agregado (`feito`, `saldo`).
Isso não permite responder "esta aula foi adiantada?" nem impedir que uma
aula concluída antes reapareça na data original.

- **Objetivo** é a regra: "inglês, 40 minutos, de segunda a sexta".
- **Ocorrência** é a obrigação concreta: "aula 12, prevista para 21/08".

A restrição `uq_objective_occurrences_objetivo_id_prevista_para` garante
que a mesma obrigação não seja gerada duas vezes — é ela que faz o
adiantamento funcionar sem duplicar trabalho.

### Pontos são um livro-razão, não um contador

`point_ledger` só recebe inserções. O total de alguém é a soma das
linhas, nunca um campo que se incrementa. Isso resolve três coisas ao
mesmo tempo:

1. dá para auditar de onde veio cada ponto;
2. um ajuste manual do responsável fica registrado como lançamento
   próprio, com autor;
3. não existe estado corrompido por atualização concorrente.

Estorno é um lançamento negativo, não uma exclusão — por isso o `CHECK`
permite valor negativo, mas proíbe zero.

`chave_idempotencia` é única: se o Android reenviar a finalização de uma
sessão porque perdeu a resposta, o segundo crédito é recusado pelo banco,
não pela aplicação.

### Sessão separa quatro contagens de tempo

| Campo | O que é |
|---|---|
| `segundos_brutos` | do início ao fim, incluindo pausas |
| `segundos_validos` | o que conta como estudo |
| `segundos_verificados` | parte com captura e heartbeat funcionando |
| `segundos_nao_verificados` | o resto — offline, permissão revogada |

Uma sessão interrompida **nunca** vira 100% verificada. Restrições `CHECK`
impedem que a soma ultrapasse o tempo bruto, então nem um bug da API
consegue inventar tempo verificado.

Todos os horários vêm do servidor. O relógio do aparelho é gravado à
parte, só como referência.

### O papel mora no vínculo, não no usuário

`family_members.papel` e não `users.papel`: a mesma pessoa pode ser
responsável na própria família e aparecer em outra depois. Toda
autorização consulta esta tabela — nunca o que o cliente afirma ser, nem
o `papel` que viaja no JWT (esse serve só para a interface decidir o que
exibir).

### Capturas ficam em disco, não no banco

`screen_captures` guarda caminho, hash SHA-256, dimensões e status —
nunca os bytes. Imagem em `bytea` incharia os backups e tornaria cada
`pg_dump` impraticável. Um teste verifica que nenhuma coluna é `bytea`.

O hash serve para dois fins: detectar reenvio duplicado
(`uq_screen_captures_sessao_id_sha256`) e provar que o arquivo não foi
trocado depois.

### UUID em vez de serial

O Android cria registros offline e envia depois. O cliente precisa saber
o id antes de o servidor responder, senão não há como ligar uma captura à
sessão que a gerou enquanto o aparelho está sem rede.

### Um ciclo de chave estrangeira, resolvido de propósito

`objective_occurrences.sessao_conclusao_id` aponta para `study_sessions`,
e `study_sessions.ocorrencia_id` aponta de volta. O PostgreSQL não cria
as duas tabelas com as duas restrições numa passada.

A saída é `use_alter=True` numa delas: a restrição entra por `ALTER TABLE`
depois que ambas existem. Sem isso, a migração inicial falha — e foi
exatamente o que a geração do DDL apontou antes de qualquer banco existir.

### Enums no banco, não só no Python

Os 14 tipos são enums nativos do PostgreSQL. O banco recusa valor
inválido mesmo que alguém escreva direto por SQL, sem passar pela API.

### Índice parcial para notificações

```sql
CREATE INDEX ix_notifications_nao_lidas ON notifications
  (destinatario_id, criada_em) WHERE lida_em IS NULL;
```

A consulta frequente é "não lidas deste usuário". Um índice parcial cobre
exatamente esse caso e não cresce com o histórico já lido.

## Rodar as migrações

```bash
cd backend
export DATABASE_URL="postgresql+asyncpg://usuario:senha@host:5432/devlog"
alembic upgrade head            # aplica
alembic upgrade head --sql      # só mostra o SQL, sem tocar no banco
alembic downgrade -1            # volta uma revisão
```

Em produção, `alembic upgrade head` é etapa controlada da implantação,
antes de liberar a versão nova — nunca automático na subida do container.

## O que ainda falta

As tabelas existem; a lógica que as usa não. Faltam repositórios,
serviços, endpoints e os testes de integração contra um PostgreSQL de
verdade — que dependem da conexão pendente (P1 em `pendencias.md`).
