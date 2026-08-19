# Checklist de testes manuais — comportamento a preservar

Roteiro para validar que nenhuma funcionalidade regrediu. Deve ser executado ao
final de cada fase, comparando com o comportamento da branch
`backup/v1.1-mvp-localstorage`.

Marcar: ✅ passou · ❌ falhou · ⬜ não testado

## Entrada

| # | Cenário | Esperado | v1.1 |
|---|---|---|---|
| 1 | Abrir o app sem conta | Cai na tela de Login | ⬜ |
| 2 | Entrar sem conta cadastrada | Erro "Nenhuma conta neste aparelho" | ⬜ |
| 3 | Cadastrar com nome < 2 caracteres | Erro "Escreva seu nome" | ⬜ |
| 4 | Cadastrar com e-mail inválido | Erro "Email inválido" | ⬜ |
| 5 | Cadastrar com senha < 4 caracteres | Erro sobre tamanho da senha | ⬜ |
| 6 | Cadastrar com senhas diferentes | Erro "As senhas não são iguais" | ⬜ |
| 7 | Cadastrar sem aceitar os termos | Erro sobre os termos | ⬜ |
| 8 | Cadastro válido | Vai para Home + modal "Conta criada" | ⬜ |
| 9 | Login com senha errada | Erro "Email ou senha não conferem" | ⬜ |
| 10 | Login correto | Entra na Home | ⬜ |
| 11 | Recuperar senha com e-mail correto | Permite definir nova senha | ⬜ |
| 12 | Recarregar a página depois de logado | Continua logado | ⬜ |

## Objetivos (CRUD)

| # | Cenário | Esperado | v1.1 |
|---|---|---|---|
| 13 | Salvar sem nome | Erro "Escreva o nome do objetivo" | ⬜ |
| 14 | Salvar com quantidade 0 | Erro sobre quantidade | ⬜ |
| 15 | Salvar com total negativo | Erro sobre total | ⬜ |
| 16 | Criar objetivo de estudo diário em horas | Aparece na lista e em Estudar | ⬜ |
| 17 | Criar tarefa mensal por vezes | Aparece com contador "0 de N" | ⬜ |
| 18 | Editar objetivo | Formulário preenchido, título vira "Editar Objetivo" | ⬜ |
| 19 | Salvar edição | Lista reflete a mudança | ⬜ |
| 20 | Excluir objetivo | Modal de confirmação e remoção | ⬜ |
| 21 | Buscar objetivo pelo nome | Filtra a lista | ⬜ |

## Estudar e cronômetro

| # | Cenário | Esperado | v1.1 |
|---|---|---|---|
| 22 | Separação por frequência | Blocos diária, semanal e mensal | ⬜ |
| 23 | Abrir cronômetro pelo play | Tela de foco com meta do período | ⬜ |
| 24 | Estado inicial | Botões "Iniciar" e "Encerrar" | ⬜ |
| 25 | Tocar Iniciar | Vira "Pausar"/"Minimizar", ponto pulsa no anel | ⬜ |
| 26 | Contagem regressiva | Tempo decresce a cada segundo | ⬜ |
| 27 | Pausar | Tempo congela e é salvo | ⬜ |
| 28 | Minimizar rodando | Fecha o foco, tarja continua contando | ⬜ |
| 29 | Encerrar pausado | Sai e salva o tempo feito | ⬜ |
| 30 | Zerar o cronômetro | Objetivo concluído automaticamente | ⬜ |
| 31 | Abrir outro objetivo com cronômetro ativo | Pergunta se quer trocar | ⬜ |
| 32 | Arrastar a tarja flutuante | Move e não volta ao canto | ⬜ |
| 33 | Tocar na tarja | Reabre o cronômetro | ⬜ |
| 34 | Botão de janela flutuante (PiP) | Abre a janela quando suportado | ⬜ |
| 35 | Marcar tarefa manualmente com ✓ | Credita e soma pontos | ⬜ |
| 36 | Desfazer conclusão | Volta ao estado anterior | ⬜ |

## Acúmulo e virada de período

| # | Cenário | Esperado | v1.1 |
|---|---|---|---|
| 37 | Objetivo acumulativo não cumprido, virar o dia | Saldo soma no próximo período | ⬜ |
| 38 | Teto de acúmulo | Diário limita a 6× a meta; demais a 3× | ⬜ |
| 39 | Objetivo não acumulativo | Não acumula pendência | ⬜ |
| 40 | Virada semanal e mensal | Recalcula na frequência certa | ⬜ |

## Home e gráficos

| # | Cenário | Esperado | v1.1 |
|---|---|---|---|
| 41 | Home sem objetivos | Mensagem orientando cadastrar | ⬜ |
| 42 | Barra do dia | Percentual coerente com o estudado | ⬜ |
| 43 | Gráfico semanal | 7 barras, domingo a sábado | ⬜ |
| 44 | Gráfico mensal | Linha do dia 1 ao fim do mês | ⬜ |
| 45 | Resumo textual | Total e média conferem | ⬜ |

## Perfil

| # | Cenário | Esperado | v1.1 |
|---|---|---|---|
| 46 | Trocar foto | Miniatura aparece na Home e no Perfil | ⬜ |
| 47 | Editar dados pessoais | Persistem após recarregar | ⬜ |
| 48 | Exportar JSON | Baixa o arquivo com o estado | ⬜ |
| 49 | Carregar exemplo | 7 objetivos e 45 dias de histórico | ⬜ |
| 50 | Apagar tudo | Confirmação e volta ao estado zerado | ⬜ |
| 51 | Sair | Volta ao Login, dados preservados | ⬜ |

## Interface e responsividade

| # | Cenário | Esperado | v1.1 |
|---|---|---|---|
| 52 | Nenhum elemento estranho sobre a navegação | Topo limpo | ⬜ |
| 53 | Rolar até o fim de uma lista longa | Último item não fica sob a barra do navegador | ⬜ |
| 54 | Nomes das abas | Objetivos (cadastro) e Estudar (execução) | ⬜ |
| 55 | Tela de 320 px de largura | Sem rolagem horizontal | ⬜ |
| 56 | Navegação por teclado | Foco visível em todos os controles | ⬜ |
| 57 | Console do navegador | Nenhum erro de JavaScript | ⬜ |
