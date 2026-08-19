# Inventário do MVP atual (v1.1) — Fase 0

Documento produzido antes de qualquer refatoração, conforme a Fase 0 do
`PROMPT_DESENVOLVIMENTO_DEVLOG_FAMILIA.md`. Descreve o que existe hoje e o que
precisa continuar funcionando depois da migração.

**Commit inventariado:** `dbdb5ce`
**Ponto de restauração:** branch `backup/v1.1-mvp-localstorage`

## 1. Estrutura dos arquivos

| Arquivo | Linhas | Papel |
|---|---|---|
| `index.html` | 1.852 | Aplicação inteira: HTML, CSS e JavaScript |
| `CLAUDE.md` | 19 | Convenção de autoria dos commits (obrigatória) |
| `PROMPT_DESENVOLVIMENTO_DEVLOG_FAMILIA.md` | 1.741 | Especificação da evolução |

Divisão interna do `index.html`:

| Faixa | Conteúdo | Linhas |
|---|---|---|
| 1–13 | `<head>`, metatags, título | 13 |
| 14–327 | `<style>` — CSS completo | 313 |
| 328–651 | Marcação das 7 telas | 324 |
| 652–1850 | `<script>` — JavaScript em IIFE | 1.198 |

O JavaScript já está organizado em 12 seções numeradas por comentário, o que
serve de mapa direto para os módulos ES da Fase 1.

## 2. Mapa das seções do JavaScript

| Seção | Linhas | Conteúdo | Destino na Fase 1 |
|---|---|---|---|
| 1. Armazenamento | 660–688 | `Store` com 3 ambientes (Claude storage, localStorage, memória) | `js/stores/storage.js` |
| 2. Estado | 689–708 | `estadoNovo()`, `E`, `salvar()` | `js/stores/app-store.js` |
| 3. Utilidades | 709–789 | datas, formatação, `esc`, `modal`, `aviso`, `bip` | `js/utils/` |
| 4. Regras de negócio | 790–898 | acúmulo, alvos, pontos, virada de período, histórico | `js/services/` |
| 5. Gráficos | 899–941 | barras e linha em SVG puro | `js/components/charts/` |
| 6. Telas | 942–1241 | `ir()` e os `render*` de cada página | `js/pages/` |
| 7. Cronômetro | 1242–1374 | sessão de foco, tique, pausa, encerrar | `js/services/timer.js` |
| 7b. Relógio flutuante | 1375–1509 | tarja arrastável e Picture-in-Picture | `js/components/floating-clock/` |
| 8. Autenticação | 1510–1550 | login/cadastro/recuperação locais | `js/auth/` (será substituído) |
| 9. Foto de perfil | 1551–1573 | leitura e compressão da imagem | `js/utils/image.js` |
| 10. Dados de exemplo | 1574–1606 | `carregarDemo()` | `js/utils/demo.js` |
| 11. Eventos | 1624–1824 | ligação dos listeners | distribuído por página |
| 12. Partida | 1825–1850 | boot da aplicação | `js/app.js` |

São 73 funções de topo, mais `soltarPiP` (async) e o módulo `Store`.

## 3. Modelo de dados atual (localStorage)

Chave única: `devlog:estado:v1`

```js
{
  usuario: {nome, email, senha, foto, nasc, sexo, escola, pais, termos} | null,
  logado: boolean,
  itens: [ /* objetivos, ver abaixo */ ],
  hist: { "AAAA-MM-DD": {min, tarefas, pontos} },
  pontos: number,
  concluidos: number,
  versao: 1
}
```

Estrutura de um item (objetivo):

```js
{
  id, tipo: "estudo"|"tarefa", nome, cat, freq: "diaria"|"semanal"|"mensal",
  qtd, uni: "horas"|"minutos"|"vezes", alvo /* minutos ou vezes */,
  totalMeta, acum: boolean, status: "andamento"|"concluido",
  feito, saldo /* pendência acumulada */, progresso,
  periodoRef, criadoEm, ultimaConclusao, desfazer?
}
```

Este é o formato que o endpoint de importação da Fase 8 (seção 18 da
especificação) terá que aceitar.

## 4. Telas existentes

| id | Nome visível | Papel |
|---|---|---|
| `tela-login` | Login | entrada |
| `tela-cadastro` | Criar conta | entrada |
| `tela-esqueci` | Recuperar senha | entrada |
| `tela-home` | Home | painel pessoal |
| `tela-objetivos` | Objetivos | CRUD de objetivos |
| `tela-estudar` | Estudar | execução das tarefas do dia |
| `tela-perfil` | Perfil | conta, exportação, exemplo, sair |

Navegação: `Objetivos · Home · Estudar · Perfil`, controlada por `TELAS_INTERNAS`.

## 5. Funcionalidades que precisam ser preservadas

- Cadastro, login e recuperação de senha (serão trocados por API real, mas o
  fluxo de telas permanece).
- CRUD de objetivos com tipo estudo/tarefa, categoria, frequência diária,
  semanal e mensal, meta em horas/minutos/vezes e total geral.
- Acúmulo de pendências com teto (`tetoAcumulo`: 6× a meta em objetivos
  diários, 3× nos demais).
- Virada automática de período (`virarPeriodos`).
- Cronômetro com contagem regressiva, pausa, retomada, encerramento e
  gravação parcial a cada 30 segundos.
- Relógio flutuante arrastável e Picture-in-Picture.
- Gráficos semanal e mensal em SVG puro, sem biblioteca.
- Pontuação, histórico diário e sequência.
- Foto de perfil com compressão no cliente.
- Exportação do estado em JSON.
- Carga de dados de exemplo.
- Identidade visual: tokens de cor, cartões lavanda, navegação em cápsula.

## 6. Riscos identificados

| # | Risco | Gravidade | Tratamento previsto |
|---|---|---|---|
| R1 | Senha gravada em texto puro no `localStorage` e comparada no cliente (`entrar()`, linha 1514) | **Alta** | Seção 12: Argon2 no servidor. A senha legada nunca deve ser importada. |
| R2 | Qualquer pessoa com acesso ao aparelho lê e edita todo o estado pelo DevTools | Alta | Persistência no PostgreSQL com autorização por usuário. |
| R3 | Tempo e pontos calculados só no cliente — trivial de fraudar | Alta | Seção 23: cronômetro e pontos validados no servidor. |
| R4 | Estado global mutável `E` acessado por 73 funções sem camada de acesso | Média | Fase 1: separar store, serviços e interface. |
| R5 | Repositório é **público** e a especificação descreve produto comercial, arquitetura e estratégia de monitoramento | Média | Seção 2 recomenda migrar para repositório privado. |
| R6 | Sem `.gitignore` — um `.env` futuro pode ser commitado por acidente | Média | Criar `.gitignore` antes da Fase 2. |
| R7 | Perda total dos dados se o usuário limpar o navegador | Média | Resolvido pela migração ao servidor. |
| R8 | Push de tags bloqueado pelo proxy desta sessão (HTTP 403) | Baixa | Ponto de restauração feito em branch. |
| R9 | Captura de tela e localização de dependentes têm exigências legais (LGPD, consentimento do menor) | **Alta** | Tratar antes da Fase 9, não só tecnicamente. |

## 7. Verificação de segredos

Varredura por chaves, tokens, senhas embutidas e blocos de chave privada:
nenhuma ocorrência. Não existe `.env` no repositório. Não existe `.gitignore`.
