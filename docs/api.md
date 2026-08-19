# API

Base: `/api/v1`. Documentação interativa em `/api/docs` (desligada em
produção — ela expõe a superfície inteira para quem não precisa vê-la).

## Autenticação

| Método | Rota | Quem pode |
|---|---|---|
| `POST` | `/auth/cadastrar` | público |
| `POST` | `/auth/entrar` | público |
| `POST` | `/auth/renovar` | cookie de refresh |
| `POST` | `/auth/sair` | qualquer sessão |
| `POST` | `/auth/sair-de-todos` | autenticado |
| `GET` | `/auth/eu` | autenticado |
| `POST` | `/auth/dependentes` | **só responsável** |

O login devolve `access_token` no corpo e grava o refresh em cookie
`HttpOnly` com caminho `/api/v1/auth`. O front guarda o access token em
memória e chama `/auth/renovar` quando ele expira (15 minutos).

## Objetivos

| Método | Rota | Quem pode |
|---|---|---|
| `POST` | `/objetivos` | **só responsável** |
| `GET` | `/objetivos` | autenticado (dependente vê só os dele) |
| `GET` | `/objetivos/{id}` | autenticado |
| `PATCH` | `/objetivos/{id}` | **só responsável** |
| `DELETE` | `/objetivos/{id}` | **só responsável** |

`DELETE` exclui de fato apenas quando não existe histórico. Com pontos ou
conclusões, arquiva e responde `{"excluido": false}` — apagar levaria
junto o histórico que justifica os pontos já creditados.

Criar um objetivo já materializa a agenda; sem isso ele nasceria sem
obrigação nenhuma e não apareceria na tela Estudar.

## Ocorrências

| Método | Rota | O que faz |
|---|---|---|
| `GET` | `/ocorrencias?de=&ate=&titular_id=` | agenda do período |
| `POST` | `/ocorrencias/{id}/progresso` | soma tempo ou repetições |
| `POST` | `/ocorrencias/{id}/concluir` | fecha e credita pontos |
| `POST` | `/ocorrencias/{id}/desfazer` | reabre com lançamento de estorno |
| `GET` | `/ocorrencias/{id}/proxima` | alimenta o "adiantar a próxima?" |

`GET /ocorrencias` materializa o que faltar e marca como perdidas as
pendências vencidas antes de responder.

## Fluxo do adiantamento

```
1. GET  /ocorrencias                    → a de hoje e a de amanhã
2. GET  /ocorrencias/{hoje}/proxima     → pode_adiantar: false
                                          motivo: "Conclua a atividade de hoje…"
3. POST /ocorrencias/{hoje}/concluir    → momento: "on_time"
4. GET  /ocorrencias/{hoje}/proxima     → pode_adiantar: true
5. POST /ocorrencias/{amanha}/concluir  → momento: "early", dias_adiantados: 1
```

Depois do passo 5, a ocorrência **mantém** `prevista_para` no dia
seguinte. É isso que faz o painel de amanhã mostrar "concluída
antecipadamente" em vez de cobrar a atividade de novo.

Os pontos caem no dia real do estudo, não na data prevista — então uma
aula adiantada não infla o dia de amanhã nem conta um dia futuro na
sequência.

## Erros

| Código | Quando |
|---|---|
| `401` | sem token, token inválido ou expirado |
| `403` | autenticado, mas sem permissão para a ação |
| `404` | não existe **ou** é de outra família |
| `409` | username ou e-mail já em uso |
| `422` | corpo não passou na validação |

O `404` para recurso de outra família é deliberado: um `403` confirmaria
que aquele id existe.

## Regras que o servidor garante

- Senha nunca trafega nem é guardada em texto puro.
- O papel no JWT serve só para a interface decidir o que exibir; toda
  autorização lê `family_members` no banco.
- Concluir a mesma ocorrência duas vezes credita uma vez só.
- Teto diário de pontos por objetivo, quando configurado.
- Dependente pontua apenas minutos verificados.
- Adiantamento respeita a ordem da fila, exige a atividade de hoje
  concluída e obedece ao limite do objetivo.
