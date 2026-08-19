# PROMPT MESTRE — EVOLUÇÃO DO DEVLOG PARA PLATAFORMA FAMILIAR WEB E ANDROID

> Copie este documento completo e entregue ao agente de desenvolvimento. Ele deve ser tratado como especificação funcional, técnica, arquitetural e de implantação. O trabalho deve ser executado por etapas, preservando o que já funciona e validando cada etapa antes de avançar.

## 1. PAPEL DO AGENTE

Atue como arquiteto de software, desenvolvedor full stack Python/JavaScript, desenvolvedor Android Kotlin, especialista em PostgreSQL, segurança de aplicações, Docker e implantação no EasyPanel.

Você deverá evoluir um MVP existente chamado **DevLog** para uma plataforma familiar de organização, execução e acompanhamento de estudos, tarefas, metas, pontuação e recompensas.

Não crie apenas telas demonstrativas. Entregue uma aplicação funcional, segura, testada, documentada e preparada para implantação real.

Trabalhe obrigatoriamente por fases. Ao concluir cada fase:

1. execute os testes correspondentes;
2. corrija os erros encontrados;
3. registre claramente o que foi implementado;
4. liste arquivos criados e alterados;
5. informe comandos necessários para testar;
6. aguarde aprovação antes de iniciar a fase seguinte, salvo autorização expressa para continuar automaticamente.

Não apague funcionalidades existentes sem justificativa e aprovação. Não reescreva tudo de uma única vez. Faça migração incremental.

---

## 2. PROJETO EXISTENTE E FONTE DE VERDADE INICIAL

Repositório atual:

- GitHub: `https://github.com/RicardovSantos/study-eneven`
- Aplicação publicada: `https://ricardovsantos.github.io/study-eneven/`
- Branch principal: `main`
- Idioma da interface: português do Brasil (`pt-BR`)
- Nome atual do produto: **DevLog**
- Versão visível atual: `1.1`

Estado atual observado:

- `index.html` concentra HTML, CSS e JavaScript em um único arquivo com aproximadamente 1.850 linhas;
- existe `CLAUDE.md` com regras de autoria dos commits, que deve ser respeitado;
- persistência atual em `localStorage`, usando a chave `devlog:estado:v1`;
- autenticação atual é apenas local e armazena dados no navegador;
- já existem cadastro, login local, recuperação local de senha, perfil, foto, objetivos, tarefas, estudos, frequências diária/semanal/mensal, pendências acumulativas, cronômetro, gráficos, pontos, histórico, exportação JSON, dados de exemplo e uma faixa flutuante/Picture-in-Picture web;
- as telas atuais incluem Home/Início, Objetivos, Estudar e Perfil;
- o visual atual e seus design tokens devem ser preservados e refinados, não descartados sem necessidade.

Antes de qualquer alteração:

1. ler completamente `CLAUDE.md`;
2. inventariar a estrutura e o funcionamento atual;
3. criar uma branch de trabalho;
4. criar uma tag ou ponto de restauração da versão funcional atual;
5. executar um teste manual das funções existentes;
6. documentar as funções que precisam ser preservadas;
7. garantir que nenhum segredo, senha, token ou `.env` seja enviado ao GitHub.

Como o repositório atual é público e o produto poderá se tornar comercial, recomendar a continuidade do desenvolvimento sensível em repositório privado, preservando o histórico quando possível.

---

## 3. OBJETIVO DO PRODUTO

Transformar o DevLog em uma aplicação web e Android para:

- organizar estudos, aulas, cursos, tarefas e metas pessoais;
- combater procrastinação;
- acompanhar tempo efetivamente realizado;
- permitir que um responsável cadastre e gerencie dependentes;
- permitir login individual do responsável e de cada dependente;
- permitir que o responsável acompanhe tarefas, sessões, capturas, localizações, pontos, níveis, recompensas e histórico do dependente;
- permitir que o próprio responsável use o aplicativo para seus estudos e configure recompensas pessoais;
- permitir sessões normais e sessões verificadas;
- funcionar pela internet em diferentes aparelhos;
- atualizar o painel do responsável em tempo real;
- funcionar inicialmente na web e, posteriormente, ser empacotado como APK Android com recursos nativos.

A aplicação não deve executar monitoramento escondido. Captura de tela, localização e sobreposição devem ficar ativas somente durante uma sessão verificada iniciada conscientemente no Android, com autorizações do sistema e indicação visível.

---

## 4. ORDEM OBRIGATÓRIA DE ENTREGA

O projeto deve ser desenvolvido nesta ordem:

1. preservar e documentar a versão atual;
2. separar HTML, CSS e JavaScript;
3. estabilizar a versão web ainda com dados locais;
4. criar backend Python, banco PostgreSQL e migrações;
5. substituir autenticação e persistência locais por autenticação e API reais;
6. implementar famílias, papéis e permissões;
7. implementar objetivos, ocorrências, estudos, tarefas e sessões;
8. implementar dashboards, pontos, níveis, recompensas e históricos;
9. implementar WebSocket e atualizações em tempo real;
10. implantar e validar toda a versão web no EasyPanel;
11. empacotar o front-end com Capacitor para Android;
12. adicionar módulos nativos Kotlin para sessão verificada;
13. gerar, assinar e testar o APK;
14. documentar instalação, atualização, backup e recuperação.

Não começar a versão Android antes de a versão web e a API estarem implantadas, seguras e estáveis.

---

## 5. TECNOLOGIAS OBRIGATÓRIAS

### 5.1 Front-end web

Utilizar:

- HTML5 semântico;
- CSS3 separado do HTML;
- JavaScript moderno separado do HTML, usando módulos ES;
- Vite como ferramenta de desenvolvimento e build do front-end Vanilla JS;
- Fetch API para REST;
- WebSocket nativo no navegador para tempo real;
- Chart.js somente se os gráficos atuais em SVG puro se tornarem difíceis de manter; se os gráficos atuais forem suficientes, preservar a implementação sem dependência desnecessária;
- PWA Manifest e Service Worker apenas depois da aplicação web principal estar estável.

Não introduzir React, Vue ou outro framework apenas por conveniência. A primeira evolução deve preservar Vanilla JavaScript e modularizar o código atual.

### 5.2 Backend web

Utilizar Python com:

- Python 3.12 ou versão estável suportada no ambiente;
- FastAPI;
- Uvicorn;
- Pydantic e `pydantic-settings`;
- SQLAlchemy 2;
- driver PostgreSQL assíncrono, preferencialmente `asyncpg`;
- Alembic para migrações;
- PyJWT para tokens;
- `pwdlib[argon2]` para hash de senhas;
- `python-multipart` para uploads;
- Pillow para miniaturas, compressão adicional e marca d'água no servidor;
- Redis para Pub/Sub em produção, distribuição de eventos e tarefas que precisem sobreviver a mais de uma instância;
- Pytest e Pytest Asyncio;
- Ruff para lint e formatação.

### 5.3 Banco e infraestrutura

Utilizar:

- PostgreSQL 17 em serviço próprio do EasyPanel;
- Redis em serviço próprio do EasyPanel ou no Compose da aplicação;
- Docker e Dockerfiles separados para front-end e backend;
- Docker Compose para os componentes estreitamente relacionados;
- Nginx como servidor dos arquivos web e proxy reverso interno para `/api` e `/ws`;
- volume persistente privado para capturas e anexos no MVP;
- abstração de armazenamento que permita migrar depois para S3 compatível;
- EasyPanel em VPS da Hostinger;
- HTTPS obrigatório.

### 5.4 Android

Utilizar:

- Capacitor para empacotar o front-end web;
- Android Studio;
- Kotlin para as funções nativas;
- `MediaProjectionManager` e `MediaProjection` para captura autorizada da tela;
- `ImageReader` para obter imagens da projeção;
- Foreground Service para manter a sessão funcionando quando o app for minimizado;
- `FusedLocationProviderClient` para localização;
- `WindowManager` com `TYPE_APPLICATION_OVERLAY` para a bolha/cronômetro flutuante;
- Room para fila e estado local nativo que precisem sobreviver a interrupções;
- WorkManager para reenvio de capturas pendentes e trabalhos persistentes adequados;
- OkHttp ou Retrofit para uploads nativos;
- Android Keystore/armazenamento criptografado para tokens do aplicativo;
- plugin Capacitor local em Kotlin para conectar JavaScript às funções nativas.

---

## 6. ESTRUTURA DE PASTAS DESEJADA

Começar a refatoração por esta estrutura. Ajustes são permitidos se forem documentados e justificados.

```text
study-eneven/
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── public/
│   │   ├── icons/
│   │   ├── images/
│   │   └── manifest.webmanifest
│   └── src/
│       ├── css/
│       │   ├── tokens.css
│       │   ├── reset.css
│       │   ├── layout.css
│       │   ├── components.css
│       │   ├── pages.css
│       │   └── responsive.css
│       └── js/
│           ├── app.js
│           ├── router.js
│           ├── config.js
│           ├── api/
│           │   ├── client.js
│           │   ├── auth.js
│           │   ├── objectives.js
│           │   ├── sessions.js
│           │   ├── families.js
│           │   └── rewards.js
│           ├── auth/
│           │   ├── session.js
│           │   └── permissions.js
│           ├── realtime/
│           │   └── socket.js
│           ├── stores/
│           │   ├── auth-store.js
│           │   ├── app-store.js
│           │   └── session-store.js
│           ├── components/
│           ├── pages/
│           │   ├── login/
│           │   ├── home/
│           │   ├── objectives/
│           │   ├── study/
│           │   ├── family/
│           │   ├── progress/
│           │   ├── rewards/
│           │   └── profile/
│           └── utils/
├── backend/
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── alembic/
│   ├── tests/
│   └── app/
│       ├── main.py
│       ├── core/
│       │   ├── config.py
│       │   ├── security.py
│       │   ├── logging.py
│       │   └── exceptions.py
│       ├── db/
│       │   ├── base.py
│       │   ├── session.py
│       │   └── migrations.py
│       ├── models/
│       ├── schemas/
│       ├── repositories/
│       ├── services/
│       ├── api/
│       │   └── v1/
│       │       ├── auth.py
│       │       ├── users.py
│       │       ├── families.py
│       │       ├── objectives.py
│       │       ├── occurrences.py
│       │       ├── sessions.py
│       │       ├── captures.py
│       │       ├── locations.py
│       │       ├── points.py
│       │       ├── rewards.py
│       │       ├── notifications.py
│       │       └── dashboard.py
│       ├── realtime/
│       │   ├── manager.py
│       │   └── events.py
│       ├── storage/
│       └── jobs/
├── android/
│   ├── capacitor.config.ts
│   └── app/src/main/
│       ├── AndroidManifest.xml
│       └── java/br/com/eneven/devlog/
│           ├── plugins/
│           ├── services/
│           ├── capture/
│           ├── location/
│           ├── overlay/
│           ├── storage/
│           └── network/
├── infra/
│   ├── docker-compose.dev.yml
│   ├── docker-compose.production.yml
│   ├── .env.example
│   └── easypanel/
│       └── README.md
├── docs/
│   ├── architecture.md
│   ├── database.md
│   ├── api.md
│   ├── authentication.md
│   ├── realtime.md
│   ├── android.md
│   ├── privacy-security.md
│   └── deployment-easypanel.md
├── scripts/
├── CLAUDE.md
└── README.md
```

Regras obrigatórias:

- não manter CSS extenso dentro do HTML;
- não manter JavaScript extenso dentro do HTML;
- não criar um único `app.js` gigantesco;
- não duplicar o CRUD de objetivos entre as páginas Objetivos e Família; reutilizar o mesmo componente/serviço;
- separar regra de negócio, acesso a dados e interface;
- manter nomes de arquivos e funções legíveis em inglês ou português, mas escolher um padrão único e documentá-lo;
- manter textos da interface em português do Brasil.

---

## 7. NAVEGAÇÃO E PERMISSÕES POR PAPEL

### 7.1 Administrador/responsável

Menu recomendado:

```text
Início | Objetivos | Estudar | Família | Perfil
```

O botão **Estudar** deve ficar visualmente destacado no centro da navegação mobile.

O responsável poderá:

- criar e editar sua própria conta;
- criar família;
- adicionar um ou mais dependentes;
- criar credenciais iniciais do dependente;
- redefinir a senha do dependente, sem conseguir visualizar a senha atual;
- criar, editar, pausar, arquivar e organizar objetivos pessoais;
- criar, editar, pausar, arquivar e organizar objetivos dos dependentes;
- iniciar suas próprias sessões de estudo;
- acompanhar dependentes em tempo real;
- visualizar capturas e localizações de sessões autorizadas;
- aprovar conclusões quando necessário;
- configurar pontos, níveis e recompensas pessoais e familiares;
- visualizar históricos, notificações e relatórios.

### 7.2 Dependente

Menu recomendado:

```text
Início | Progresso | Estudar | Recompensas | Perfil
```

O dependente não poderá acessar `Família` nem o CRUD administrativo de `Objetivos`.

O dependente poderá:

- entrar com login próprio;
- visualizar tarefas e estudos atribuídos;
- iniciar, pausar, retomar e concluir sessões;
- iniciar sessão verificada no Android;
- solicitar ou executar adiantamento quando autorizado;
- visualizar o próprio progresso;
- visualizar pontos, níveis e recompensas;
- enviar resumo ou comprovante final;
- atualizar apenas informações pessoais permitidas.

### 7.3 Regra de segurança

Esconder botões no front-end não é segurança. Toda operação deve ser validada pelo backend considerando:

- usuário autenticado;
- família;
- papel na família;
- titular do recurso;
- relação responsável/dependente;
- permissões específicas;
- estado atual da entidade.

Um dependente nunca deve conseguir alterar o papel da própria conta, excluir histórico, mudar pontos, criar recompensas, modificar configurações de monitoramento ou acessar dados de outra pessoa.

---

## 8. ESPECIFICAÇÃO DAS PÁGINAS

## 8.1 Início — administrador

Exibir:

- foto, nome e saudação;
- nível atual pessoal;
- pontuação pessoal total;
- progresso para o próximo nível;
- pontuação pessoal por matéria/categoria;
- tempo estudado hoje, na semana e no mês;
- quantidade de conclusões;
- sequência de dias estudando;
- gráficos de progresso preservando a identidade visual atual;
- seção “Minha família” com cartão resumido de cada dependente;
- status do dependente: estudando, pausado, offline, sessão interrompida ou sem tarefa ativa;
- tempo estudado do dependente hoje;
- objetivos concluídos e atrasados;
- nível e próximo prêmio do dependente;
- últimas notificações relevantes;
- histórico recente limitado a dez registros;
- botão “Ver histórico completo” com paginação e filtros.

O histórico recente deve permitir filtrar por usuário, tipo, matéria e período.

## 8.2 Início — dependente

Exibir:

- foto e saudação;
- meta de hoje;
- nível atual;
- pontos totais;
- pontos por matéria;
- progresso para o próximo nível;
- nome do próximo prêmio;
- quanto falta em pontos/minutos;
- tempo estudado hoje e na semana;
- sequência de dias;
- atividades concluídas;
- atividades atrasadas;
- últimas dez atividades;
- botão “Ver histórico completo”.

## 8.3 Estudar

Esta página é para execução, não para CRUD.

Separar em:

- Estudos para fazer;
- Tarefas para fazer;
- Concluídas hoje, recolhidas por padrão.

Cada cartão deve mostrar:

- nome;
- matéria/categoria;
- frequência;
- data prevista;
- tempo ou quantidade planejada;
- realizado;
- restante;
- pendência acumulada;
- pontos possíveis;
- necessidade ou não de sessão verificada;
- botão Iniciar, Retomar ou Concluir.

Durante uma sessão exibir:

- cronômetro grande;
- tempo realizado e restante;
- nome e matéria;
- meta do período;
- estado: ativa, pausada, interrompida ou finalizada;
- captura ativa/inativa;
- localização ativa/inativa;
- horário da última captura;
- horário estimado da próxima captura;
- conectividade;
- botões Pausar, Finalizar e Minimizar;
- aviso transparente sobre monitoramento quando for sessão verificada.

## 8.4 Família — somente administrador

Exibir:

- seletor de dependentes por foto;
- botão Adicionar dependente;
- engrenagem de configurações do dependente selecionado;
- foto, nome, nível e status;
- dashboard diário, semanal e mensal;
- pontuação total e por matéria;
- objetivos concluídos e atrasados;
- sessão ativa;
- captura mais recente;
- última localização registrada e precisão;
- notificações recentes;
- histórico limitado a 10 ou 15 linhas;
- botão Ver histórico completo.

Configurações do dependente:

- conta, foto, nome e login;
- redefinição de senha;
- relação familiar;
- dispositivos autorizados;
- locais cadastrados;
- regras de sessão verificada;
- intervalo de captura, com padrão de oito minutos;
- exigência de localização;
- exigência de resumo/comprovante;
- regras de pontuação;
- níveis e recompensas;
- notificações;
- objetivos, reutilizando o CRUD central;
- desativação de conta.

## 8.5 Objetivos — somente administrador

CRUD completo para objetivos pessoais e dos dependentes.

Campos:

- titular: Eu ou dependente;
- tipo: estudo ou tarefa;
- nome;
- matéria/categoria;
- descrição;
- status;
- meta em tempo ou quantidade;
- total geral do curso/tarefa, se aplicável;
- frequência diária, semanal, mensal ou personalizada;
- dias da semana;
- horário recomendado;
- data de início;
- prazo final;
- acumular pendências;
- permitir adiantamento;
- quantidade máxima que pode ser adiantada;
- adiantamento automático ou sujeito à aprovação;
- exigir sessão verificada;
- limite diário de pontos;
- pontos fixos para tarefa sem cronômetro;
- necessidade de aprovação final.

Ações:

- criar;
- editar;
- duplicar;
- pausar;
- reativar;
- arquivar;
- excluir apenas quando não existir histórico relacionado.

Objetivos com sessões ou pontos devem ser arquivados, nunca apagados silenciosamente.

## 8.6 Perfil

Para todos:

- foto;
- nome e informações pessoais;
- alteração de senha;
- preferências do aplicativo;
- tema;
- notificações;
- dispositivos;
- permissões Android;
- backup/exportação dos próprios dados quando permitido;
- privacidade;
- sair.

Para administrador:

- minhas recompensas;
- configurações gerais da família;
- gerenciamento e retenção de dados;
- logs administrativos relevantes.

---

## 9. OBJETIVOS, OCORRÊNCIAS E ADIANTAMENTO

Não controlar recorrência apenas com um contador agregado. Separar:

- **Objetivo:** regra geral, por exemplo “Curso de inglês, 40 minutos de segunda a sexta”;
- **Ocorrência:** obrigação específica, por exemplo “Aula 12 prevista para 21/08/2026”.

Cada ocorrência deve possuir:

- objetivo;
- titular;
- data prevista;
- status;
- meta da ocorrência;
- realizado;
- data/hora de conclusão;
- se foi concluída no prazo, atrasada ou adiantada;
- quantos dias foi adiantada;
- sessão associada;
- pontos gerados.

### Adiantar próxima atividade

Após concluir a ocorrência atual, mostrar:

```text
Próxima aula: Aula 12
Prevista para amanhã — 40 minutos
[Adiantar próxima aula]
```

Regras:

- só permitir se o objetivo estiver configurado para adiantamento;
- por padrão, exigir conclusão da obrigação atual;
- por padrão, liberar apenas a próxima ocorrência;
- respeitar a ordem das aulas;
- permitir que o responsável configure até quantas ocorrências podem ser adiantadas;
- permitir modo automático ou solicitação de aprovação;
- registrar data prevista e data real;
- não gerar novamente a ocorrência já concluída antecipadamente;
- pontuar no dia real em que o estudo aconteceu;
- não contar um dia futuro como dia estudado na sequência;
- mostrar no dia previsto “Concluída antecipadamente”.

Evento para o responsável:

```text
Pedro adiantou a Aula 12 de inglês, prevista para amanhã.
```

---

## 10. PONTOS, NÍVEIS E RECOMPENSAS

### 10.1 Pontuação

Regra padrão:

- um minuto válido de estudo = um ponto;
- segundos incompletos devem acumular para não serem perdidos;
- pausas não contam;
- para dependentes, o padrão é pontuar apenas minutos verificados;
- tarefas sem cronômetro recebem pontos fixos configurados pelo administrador;
- pontos devem ser calculados e validados pelo servidor;
- permitir limite diário por objetivo;
- impedir geração ilimitada de pontos deixando o cronômetro ligado;
- toda alteração manual deve gerar auditoria.

Não armazenar somente um total mutável. Criar um livro-razão de pontos (`point_ledger`) imutável, com origem, usuário, objetivo, sessão, quantidade e data.

### 10.2 Trilhas de recompensa

Permitir trilhas:

- geral: soma todos os objetivos selecionados;
- por matéria/categoria;
- por objetivo específico;
- por conjunto selecionado de objetivos.

Cada trilha pertence a um beneficiário, que pode ser dependente ou administrador.

Exemplo:

```text
Trilha: Inglês
Nível 1 — 100 pontos — prêmio: escolher uma sobremesa
Nível 2 — 200 pontos — prêmio: uma hora extra de videogame
Nível 3 — 300 pontos — prêmio: escolher um passeio
[+ Adicionar nível]
```

Regras:

- níveis numerados automaticamente;
- limites obrigatoriamente crescentes;
- pontos acumulativos;
- desbloquear prêmio ao alcançar o limite;
- não descontar pontos ao desbloquear;
- status do prêmio: bloqueado, desbloqueado, solicitado e entregue;
- responsável confirma a entrega;
- usuário visualiza claramente quanto falta;
- administrador pode configurar recompensas pessoais para se incentivar.

Uma loja de recompensas repetíveis deve ser tratada como evolução futura, não misturada ao MVP de níveis.

---

## 11. MODELO DE DADOS POSTGRESQL

Criar migrações Alembic desde o início. Todas as tabelas devem possuir `id`, datas de criação/atualização adequadas e índices coerentes.

Tabelas mínimas:

### `users`

- `id` UUID;
- `username` único;
- `email` único e opcional para dependentes;
- `password_hash`;
- `display_name`;
- `avatar_path`;
- `birth_date` opcional;
- `active`;
- `last_login_at`;
- timestamps.

### `families`

- `id` UUID;
- `name`;
- `owner_user_id`;
- configurações padrão de pontos, captura, localização e retenção;
- timestamps.

### `family_members`

- `family_id`;
- `user_id`;
- `role`: `admin` ou `dependent`;
- `relationship`;
- `status`;
- `created_by`;
- timestamps;
- restrição única por família/usuário.

### `refresh_tokens`

- usuário;
- hash do token;
- dispositivo;
- expiração;
- revogação;
- IP e user agent quando apropriado.

### `devices`

- usuário;
- identificador da instalação;
- plataforma;
- modelo;
- versão do Android;
- versão do app;
- capacidades: captura, localização, overlay;
- último acesso;
- revogado.

### `subjects`

- família;
- nome;
- cor/ícone;
- ativo.

### `objectives`

- titular;
- criador;
- família;
- tipo `study` ou `task`;
- assunto/categoria;
- nome e descrição;
- meta;
- unidade;
- frequência;
- agenda;
- acumulação;
- total geral;
- verificação exigida;
- adiantamento permitido;
- limite de adiantamento;
- aprovação de adiantamento;
- limite diário de pontos;
- pontos fixos;
- status e arquivamento;
- timestamps.

### `objective_occurrences`

- objetivo;
- titular;
- `scheduled_for`;
- meta desta ocorrência;
- realizado;
- status;
- `completed_at`;
- `completion_timing`: no prazo, atrasada ou adiantada;
- dias adiantados;
- sessão de conclusão;
- timestamps;
- restrição contra duplicidade da mesma ocorrência.

### `study_sessions`

- ocorrência e objetivo;
- usuário e dispositivo;
- tipo normal ou verificada;
- estado;
- horário inicial do servidor;
- horário de pausa, retomada e finalização;
- segundos brutos;
- segundos válidos;
- segundos verificados;
- segundos não verificados;
- última heartbeat;
- motivo de interrupção;
- captura exigida;
- localização exigida;
- resumo final;
- aprovação;
- timestamps.

### `session_events`

- sessão;
- tipo do evento;
- data/hora do servidor;
- dados JSON estritamente validados;
- origem;
- sequência.

### `screen_captures`

- sessão;
- usuário;
- caminho privado;
- hash SHA-256;
- tamanho;
- MIME;
- largura e altura;
- capturada em;
- recebida em;
- status;
- localização associada;
- expiração/remoção;
- indicador de tela protegida ou imagem inválida.

### `known_locations`

- família;
- nome: Casa da mãe, Casa da avó, Escola etc.;
- latitude/longitude protegidas;
- raio em metros;
- ativo.

### `session_locations`

- sessão;
- captura opcional;
- latitude/longitude;
- precisão;
- horário do dispositivo e do servidor;
- localização conhecida identificada;
- `is_mock` quando disponível;
- idade da leitura;
- status de validação.

### `point_ledger`

- beneficiário;
- família;
- objetivo;
- sessão/ocorrência;
- pontos positivos ou ajuste administrativo;
- origem;
- descrição;
- criado por;
- timestamps;
- impedir duplicidade de crédito por evento.

### `reward_tracks`

- beneficiário;
- criador;
- família;
- nome;
- escopo: todos, matéria, objetivo ou conjunto;
- configuração do filtro;
- ativo.

### `reward_levels`

- trilha;
- número do nível;
- pontos necessários;
- descrição do prêmio;
- ordem;
- ativo.

### `reward_unlocks`

- nível;
- beneficiário;
- desbloqueado em;
- solicitado em;
- entregue em;
- confirmado por;
- status.

### `notifications`

- destinatário;
- família;
- tipo;
- título;
- mensagem;
- payload validado;
- lida;
- timestamps.

### `audit_logs`

- ator;
- família;
- ação;
- tipo e id do recurso;
- metadados seguros;
- IP/user agent quando adequado;
- timestamp.

Criar diagrama do banco em `docs/database.md` e justificar chaves, índices, restrições e políticas de exclusão.

---

## 12. AUTENTICAÇÃO E LOGIN

Substituir totalmente a senha em texto puro e o login local atuais.

### 12.1 Responsável

- cadastro com nome, username, e-mail e senha;
- validação de e-mail pode ser adicionada quando SMTP estiver configurado;
- login por username ou e-mail;
- senha com Argon2;
- opção de recuperação real por token de uso único e expiração;
- criação da família após primeiro login.

### 12.2 Dependente

- conta criada pelo responsável;
- username único;
- e-mail opcional;
- senha temporária definida pelo responsável;
- responsável pode redefinir a senha, mas nunca visualizar a senha atual;
- papel e vínculo definidos no banco, nunca confiados ao front-end;
- opção futura de PIN deve ser separada do mecanismo principal de autenticação.

### 12.3 Sessões

Implementar:

- access token JWT curto, por exemplo 15 minutos;
- refresh token opaco, rotativo e armazenado com hash no banco;
- revogação por dispositivo;
- logout do dispositivo atual;
- logout de todos os dispositivos;
- expiração configurável;
- limitação de tentativas de login;
- auditoria de login e redefinição de senha.

Na web:

- refresh token em cookie `HttpOnly`, `Secure` e `SameSite=Lax`;
- access token mantido apenas pelo período necessário;
- proteção CSRF para operações autenticadas por cookie, quando aplicável;
- nunca guardar senha ou refresh token em `localStorage`.

No Android:

- armazenar token sensível usando Android Keystore/armazenamento criptografado;
- o serviço nativo deve obter credencial curta e limitada para enviar heartbeat, capturas e localizações;
- revogar acesso quando o dispositivo for removido pelo responsável.

---

## 13. API REST

Versionar em `/api/v1`.

Grupos mínimos:

```text
/api/v1/auth
/api/v1/users
/api/v1/families
/api/v1/family-members
/api/v1/devices
/api/v1/subjects
/api/v1/objectives
/api/v1/occurrences
/api/v1/study-sessions
/api/v1/captures
/api/v1/locations
/api/v1/points
/api/v1/reward-tracks
/api/v1/reward-levels
/api/v1/notifications
/api/v1/dashboard
/api/v1/history
```

Requisitos:

- schemas Pydantic separados dos models SQLAlchemy;
- paginação em históricos;
- filtros por usuário, matéria, objetivo, status e período;
- respostas de erro padronizadas;
- status HTTP corretos;
- idempotência para finalização de sessão, crédito de pontos e upload repetido;
- OpenAPI do FastAPI revisada;
- health endpoints separados para vida e prontidão;
- tamanho, MIME e dimensões de upload validados;
- arquivos nunca expostos por URL pública permanente.

---

## 14. TEMPO REAL

O PostgreSQL é a fonte de verdade. WebSocket serve para avisar que algo mudou, não para substituir o banco.

Endpoint sugerido:

```text
wss://devlog.eneven.com.br/ws
```

Autenticar a conexão e criar canais isolados por usuário e família.

Eventos mínimos:

```text
session.started
session.paused
session.resumed
session.heartbeat
session.capture.created
session.location.updated
session.monitoring_interrupted
session.completed
objective.completed
occurrence.advanced
advance.requested
advance.approved
points.credited
reward.unlocked
notification.created
dependent.status_changed
```

Fluxo de conclusão:

1. aplicativo envia a conclusão para FastAPI;
2. FastAPI valida usuário, sessão e idempotência;
3. transação atualiza sessão/ocorrência, registra pontos e eventos;
4. commit no PostgreSQL;
5. publicar evento no Redis Pub/Sub;
6. processo WebSocket envia apenas aos clientes autorizados;
7. painel atualiza a área necessária;
8. se o responsável estiver offline, o evento permanece registrado e o dashboard é reconstruído pelo banco no próximo acesso.

Heartbeat padrão:

- aplicativo envia a cada 30 segundos;
- considerar interrompido após 90 segundos sem heartbeat;
- não apagar sessão automaticamente;
- separar tempo verificado e não verificado;
- reconciliação obrigatória ao reconectar.

---

## 15. SESSÃO VERIFICADA NO ANDROID

Disponível apenas no APK Android. A versão web não deve fingir que consegue monitorar outros aplicativos.

### 15.1 Fluxo

1. usuário abre uma ocorrência;
2. toca em “Iniciar estudo verificado”;
3. aplicativo valida login, dispositivo e permissões;
4. cria sessão no servidor;
5. solicita autorização do Android para captura por MediaProjection;
6. solicita localização precisa no contexto da função;
7. verifica permissão de notificações e sobreposição;
8. inicia Foreground Service visível;
9. inicia heartbeat;
10. usuário minimiza o DevLog e abre o curso externo;
11. cronômetro e bolha continuam;
12. a cada oito minutos, o serviço captura uma imagem, coleta localização e envia;
13. se estiver offline, guarda em fila criptografada/app-private e reenvia depois;
14. responsável recebe o evento em tempo real;
15. ao finalizar, parar projeção, localização, overlay e serviço; solicitar resumo e concluir no servidor.

O intervalo padrão deve ser **oito minutos**, configurável pelo responsável dentro de limites seguros. Registrar no início da sessão uma cópia da configuração usada para preservar a integridade do histórico.

### 15.2 Captura

- usar MediaProjection com consentimento do sistema em cada sessão;
- usar ImageReader para obter o frame;
- capturar somente durante a sessão ativa;
- comprimir em WebP ou JPEG com resolução suficiente para identificar o aplicativo aberto, evitando arquivo excessivo;
- calcular SHA-256;
- anexar horários do dispositivo e servidor;
- enviar por HTTPS autenticado;
- aplicar marca d'água no servidor com sessão, horário, local identificado e precisão;
- detectar frames vazios/pretos quando possível;
- não solicitar áudio;
- não solicitar câmera;
- não solicitar leitura ampla do armazenamento;
- interromper corretamente quando o Android revogar a projeção ou bloquear a tela;
- notificar o responsável sobre interrupção.

### 15.3 Localização

Coletar:

- no início;
- junto de cada captura;
- no final.

Utilizar FusedLocationProviderClient e registrar precisão, idade da leitura e `isMock` quando disponível.

Permitir cadastrar geofences conhecidas:

- Casa da mãe;
- Casa da avó;
- Escola;
- Casa do responsável;
- Outros locais.

Exibir rótulo e precisão, por exemplo:

```text
Casa da avó · precisão aproximada de 18 metros
```

Localização é evidência contextual, não prova absoluta. Não prometer que GPS ou detecção de localização simulada sejam impossíveis de burlar.

Não implementar rastreamento contínuo fora de uma sessão verificada no MVP.

### 15.4 Bolha/relógio flutuante

Criar overlay nativo próprio, não depender da Bubble API de conversas.

Características:

- círculo ou cápsula compacta;
- cronômetro atualizando a cada segundo;
- arrastável;
- toca para expandir;
- toque para abrir a tela Estudar;
- controles Pausar, Finalizar e Abrir DevLog;
- não bloquear toques fora da bolha;
- refletir tempo calculado pelo serviço/servidor, não por incrementos frágeis de JavaScript;
- aparecer somente com sessão ativa;
- manter notificação persistente como alternativa e obrigação do Foreground Service.

Estados visuais:

- roxo: sessão verificada ativa;
- amarelo: pausada ou temporariamente offline;
- vermelho: captura/localização/heartbeat interrompidos;
- verde: concluída;
- cinza: sincronização pendente.

Ao negar `SYSTEM_ALERT_WINDOW`, a sessão ainda deve funcionar pela notificação persistente, sem overlay.

### 15.5 Permissões Android

Declarar e solicitar somente o necessário:

```text
android.permission.INTERNET
android.permission.POST_NOTIFICATIONS             # Android 13+
android.permission.FOREGROUND_SERVICE
android.permission.FOREGROUND_SERVICE_MEDIA_PROJECTION  # Android 14+
android.permission.FOREGROUND_SERVICE_LOCATION          # Android 14+
android.permission.ACCESS_COARSE_LOCATION
android.permission.ACCESS_FINE_LOCATION
android.permission.SYSTEM_ALERT_WINDOW
```

Regras:

- MediaProjection exige diálogo do sistema e consentimento por sessão;
- `SYSTEM_ALERT_WINDOW` exige tela especial “Aparecer sobre outros apps”;
- solicitar localização precisa somente ao iniciar recurso que a necessita;
- não solicitar `ACCESS_BACKGROUND_LOCATION` no MVP se o caso for atendido por sessão iniciada pelo usuário e Foreground Service visível; validar no Android alvo e documentar qualquer necessidade real antes de adicionar;
- não solicitar câmera, microfone, contatos, SMS, chamadas, acessibilidade ou armazenamento amplo;
- não reiniciar monitoramento secretamente após reboot;
- exibir notificação persistente “Sessão verificada: captura e localização ativas”.

### 15.6 Interrupções

Tratar:

- permissão revogada;
- projeção encerrada;
- aplicativo forçado a parar;
- tela bloqueada;
- aparelho reiniciado;
- perda de rede;
- token expirado;
- armazenamento cheio;
- captura inválida;
- localização indisponível;
- processo morto pelo fabricante.

Nunca marcar uma sessão interrompida como totalmente verificada. Separar tempo válido, verificado e pendente.

---

## 16. PERMISSÕES E LIMITAÇÕES DA VERSÃO WEB

A versão web deve funcionar sem permissões invasivas.

Permissões possíveis:

- notificações do navegador, apenas após explicação e ação do usuário;
- seleção de arquivo/foto para perfil;
- câmera somente se futuramente houver ação explícita para tirar foto de perfil, nunca para monitoramento;
- localização apenas se houver uma função explícita e separada, nunca em segundo plano.

Não utilizar `getDisplayMedia()` como solução principal para dependente Android. Uma página web minimizada não consegue monitorar de forma confiável outros aplicativos do Android.

Quando uma ocorrência exigir verificação e o dependente estiver na web, mostrar:

```text
Esta atividade precisa ser realizada pelo aplicativo Android para habilitar captura e localização verificadas.
```

O responsável poderá usar normalmente web ou Android para administrar e acompanhar.

---

## 17. ARMAZENAMENTO E PRIVACIDADE

Capturas não devem ser armazenadas como bytea dentro do PostgreSQL.

No MVP:

- volume privado montado no backend;
- estrutura por família/usuário/sessão;
- nome interno aleatório, não confiável ao nome enviado pelo cliente;
- acesso somente por endpoint autenticado e autorizado;
- miniaturas geradas pelo servidor;
- URLs temporárias ou streaming autenticado;
- exclusão automática padrão após 15 dias, configurável para 7 ou 15 dias;
- após retenção, manter somente metadados necessários, como horário, local rotulado, hash e status, conforme configuração e política.

Exemplo interno:

```text
/app/storage/families/{family_id}/sessions/{session_id}/captures/{uuid}.webp
```

Segurança:

- HTTPS obrigatório;
- validar MIME real, dimensão e tamanho;
- remover metadados desnecessários;
- impedir path traversal;
- não servir diretório estaticamente;
- limitar taxa de upload;
- registrar auditoria de acesso administrativo às capturas;
- criar rotina de limpeza testada;
- impedir que uma família acesse arquivos de outra.

---

## 18. MIGRAÇÃO DO LOCALSTORAGE

O estado atual em `devlog:estado:v1` não deve simplesmente desaparecer.

Criar fluxo opcional e de uso único:

1. usuário entra na nova conta;
2. aplicação detecta dados legados locais;
3. apresenta resumo do que será importado;
4. solicita confirmação;
5. envia objetivos e histórico compatíveis para endpoint de importação;
6. backend valida, normaliza e impede duplicidade;
7. registra auditoria;
8. oferece exportação de backup antes de remover o legado;
9. só remove após confirmação de sucesso.

Nunca importar a senha local em texto puro. Exigir senha nova no sistema real.

---

## 19. SUBDOMÍNIO E ENDEREÇOS

Subdomínio recomendado:

```text
https://devlog.eneven.com.br
```

Usar o mesmo domínio para reduzir complexidade de CORS e cookies:

```text
Web:       https://devlog.eneven.com.br/
API:       https://devlog.eneven.com.br/api/v1/
WebSocket: wss://devlog.eneven.com.br/ws
Docs dev:  /api/docs somente em ambiente autorizado
```

Configuração DNS:

- criar registro `A` para `devlog` apontando para o IPv4 público da VPS Hostinger;
- criar registro `AAAA` somente se IPv6 estiver corretamente configurado;
- não expor PostgreSQL, Redis ou volume de mídia publicamente;
- configurar o domínio no EasyPanel apontando para o serviço web/gateway;
- ativar HTTPS e redirecionamento HTTP → HTTPS;
- testar certificado, WebSocket seguro e renovação.

---

## 20. IMPLANTAÇÃO NO EASYPANEL

Infraestrutura: VPS da Hostinger com EasyPanel.

### 20.1 Projeto

Criar projeto EasyPanel:

```text
devlog
```

### 20.2 PostgreSQL

Criar serviço PostgreSQL nativo do EasyPanel:

```text
Serviço: devlog-postgres
Versão: PostgreSQL 17
Banco: devlog
Usuário: gerar credencial forte no painel
Porta: somente rede interna
Volume: persistente
```

Copiar a string interna de conexão fornecida pelo EasyPanel e configurar no backend. Não inventar hostname nem publicar a porta 5432.

Exemplo conceitual, sem credenciais reais:

```text
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@INTERNAL_HOST:5432/devlog
```

Executar `alembic upgrade head` como etapa controlada de implantação antes de liberar a nova versão.

### 20.3 Redis

Criar serviço interno protegido:

```text
Serviço: devlog-redis
Exposição pública: não
Uso: Pub/Sub, presença, rate limiting e fila de tarefas
```

### 20.4 Aplicação

Preferência:

- Compose Service do EasyPanel apontando para o repositório privado;
- arquivo `infra/docker-compose.production.yml`;
- containers de web/gateway, API e worker;
- PostgreSQL como serviço nativo separado;
- Redis pode ser nativo separado;
- domínio direcionado ao serviço `web` na porta interna 80.

O Nginx deve:

- servir o build do front-end;
- encaminhar `/api/` para FastAPI;
- encaminhar `/ws` com headers de upgrade para WebSocket;
- aplicar limites adequados de upload;
- adicionar headers de segurança;
- não expor `/app/storage` diretamente.

### 20.5 Variáveis de ambiente

Criar `.env.example` sem valores secretos e cadastrar segredos apenas no EasyPanel.

Variáveis mínimas:

```text
ENVIRONMENT=production
APP_NAME=DevLog
APP_BASE_URL=https://devlog.eneven.com.br
API_PREFIX=/api/v1
DATABASE_URL=...
REDIS_URL=...
JWT_SECRET_KEY=...
JWT_ALGORITHM=HS256
ACCESS_TOKEN_MINUTES=15
REFRESH_TOKEN_DAYS=30
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
CORS_ORIGINS=https://devlog.eneven.com.br
STORAGE_BACKEND=local
STORAGE_PATH=/app/storage
MAX_CAPTURE_BYTES=...
CAPTURE_INTERVAL_SECONDS=480
CAPTURE_RETENTION_DAYS=15
SESSION_HEARTBEAT_SECONDS=30
SESSION_HEARTBEAT_TIMEOUT_SECONDS=90
LOCATION_WITH_CAPTURE=true
LOG_LEVEL=INFO
SMTP_HOST=
SMTP_PORT=
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
```

Gerar segredos criptograficamente fortes. Nunca colocar valores reais no Git.

### 20.6 Persistência e backup

Configurar:

- backup lógico automático do PostgreSQL no EasyPanel;
- destino externo, preferencialmente S3 compatível, e não apenas o disco da mesma VPS;
- retenção diária e semanal adequada;
- teste manual de backup;
- teste real de restauração em ambiente não produtivo;
- backup do volume de capturas conforme política de retenção;
- documentação de recuperação;
- monitoramento do espaço em disco.

Não usar cópia bruta do volume vivo do PostgreSQL como substituto de `pg_dump`/backup lógico.

### 20.7 Saúde e observabilidade

Criar:

```text
/health/live
/health/ready
```

Verificar:

- API em execução;
- conexão com PostgreSQL;
- conexão com Redis;
- volume gravável;
- migração compatível;
- logs estruturados sem senhas ou tokens;
- reinício automático dos containers;
- alertas de disco, falha de backup e indisponibilidade.

---

## 21. TESTES OBRIGATÓRIOS

### Backend

- cadastro e login;
- hash Argon2;
- refresh token, rotação e revogação;
- isolamento entre famílias;
- dependente impedido de usar rotas administrativas;
- CRUD de objetivos;
- geração de ocorrências;
- conclusão normal, atrasada e adiantada;
- idempotência;
- pontos por minuto e limite diário;
- desbloqueio de nível;
- histórico paginado;
- upload válido e inválido;
- retenção;
- WebSocket autenticado;
- reconexão e evento offline.

### Front-end

- navegação por papel;
- ausência de abas administrativas para dependente;
- dashboards vazios e preenchidos;
- últimos dez registros e Ver mais;
- CRUD;
- iniciar, pausar, retomar e finalizar;
- adiantamento;
- atualização em tempo real;
- estados de erro, loading e offline;
- acessibilidade básica;
- responsividade.

### Android em aparelho real

- login e armazenamento seguro;
- permissão de notificações;
- consentimento MediaProjection por sessão;
- captura com app minimizado;
- captura ao abrir curso externo;
- captura ao abrir outro aplicativo/jogo;
- localização e precisão;
- detecção `isMock` quando disponível;
- upload online;
- fila offline e reenvio;
- heartbeat;
- bolha arrastável;
- toque e expansão;
- pausar/finalizar pela bolha;
- fallback por notificação sem overlay;
- revogação de permissão;
- bloqueio de tela;
- reinício do aparelho;
- bateria/otimização do fabricante;
- sessão não marcada como verificada após interrupção.

Registrar modelo do aparelho e versão do Android usados nos testes.

---

## 22. ETAPAS DE IMPLEMENTAÇÃO E CRITÉRIOS DE ACEITE

## Fase 0 — Segurança do estado atual

Entregas:

- inventário;
- branch/tag de segurança;
- documentação do comportamento atual;
- lista de testes manuais;
- decisão sobre repositório privado.

Aceite: versão original continua publicável e restaurável.

## Fase 1 — Separação do front-end

Entregas:

- HTML, CSS e JS separados;
- módulos de páginas, API, estado e utilidades;
- Vite configurado;
- identidade visual preservada;
- funções existentes preservadas;
- nenhuma API real ainda, salvo abstração.

Aceite: o comportamento atual continua funcionando localmente, sem CSS/JS extenso inline.

## Fase 2 — Backend, PostgreSQL e autenticação

Entregas:

- FastAPI;
- SQLAlchemy/Alembic;
- tabelas iniciais;
- cadastro/login seguro;
- tokens;
- documentação OpenAPI;
- testes.

Aceite: dois usuários em navegadores diferentes conseguem autenticar com persistência no PostgreSQL.

## Fase 3 — Família, papéis e autorização

Entregas:

- família;
- administrador e dependente;
- criação de conta dependente;
- isolamento por família;
- menus por papel;
- testes de autorização.

Aceite: dependente não acessa nem pela interface nem diretamente pela API os recursos administrativos.

## Fase 4 — Objetivos, ocorrências e sessões

Entregas:

- CRUD;
- agenda;
- ocorrências;
- pendências;
- cronômetro baseado no servidor;
- adiantamento;
- histórico.

Aceite: atividade futura adiantada não reaparece na data original e mantém histórico correto.

## Fase 5 — Dashboards, pontos, níveis e recompensas

Entregas:

- dashboards por papel;
- resumo familiar;
- últimos dez registros;
- paginação;
- point ledger;
- trilhas e níveis;
- desbloqueios e entrega.

Aceite: pontos gerais e filtrados por matéria produzem níveis corretos sem duplicidade.

## Fase 6 — Tempo real

Entregas:

- WebSocket autenticado;
- Redis Pub/Sub;
- eventos persistidos;
- presença e heartbeat;
- reconexão.

Aceite: ao concluir uma tarefa em um dispositivo, o painel autorizado atualiza sem recarregar a página.

## Fase 7 — Deploy web no EasyPanel

Entregas:

- Dockerfiles;
- Compose de produção;
- PostgreSQL e Redis internos;
- domínio e HTTPS;
- migrações;
- volumes;
- backups;
- documentação completa.

Aceite: `https://devlog.eneven.com.br` funciona em produção, incluindo login, API, WebSocket e persistência após reinício.

## Fase 8 — APK básico com Capacitor

Entregas:

- projeto Android;
- mesmo login e permissões por papel;
- navegação adaptada;
- API de produção;
- armazenamento seguro;
- APK de teste assinado.

Aceite: administrador e dependente usam o mesmo APK com menus diferentes e dados sincronizados com a web.

## Fase 9 — Monitoramento Android transparente

Entregas:

- MediaProjection;
- Foreground Service;
- captura de oito em oito minutos;
- localização;
- upload offline/online;
- heartbeat;
- bolha flutuante;
- notificação persistente;
- eventos em tempo real;
- estados de interrupção.

Aceite: com o DevLog minimizado e um curso ou jogo aberto, a sessão continua, a bolha mostra o tempo, as capturas autorizadas chegam ao responsável com localização e interrupções são registradas.

## Fase 10 — Finalização

Entregas:

- testes finais;
- auditoria de segurança;
- documentação;
- backup/restore testado;
- APK de release assinado;
- manual de instalação do APK;
- manual de atualização;
- lista de limitações conhecidas;
- plano de evolução.

---

## 23. REGRAS DE QUALIDADE E SEGURANÇA

- Não armazenar senha em texto puro.
- Não confiar no papel informado pelo cliente.
- Não confiar no tempo calculado apenas pelo JavaScript.
- Não creditar pontos duas vezes.
- Não expor banco ou Redis na internet.
- Não expor capturas como arquivos públicos.
- Não registrar tokens, senhas ou coordenadas completas em logs.
- Não monitorar fora de sessão ativa.
- Não usar câmera, microfone, keylogger ou serviço de acessibilidade.
- Não solicitar permissões desnecessárias.
- Não permitir exclusão silenciosa de histórico financeiro de pontos ou sessões.
- Não alterar esquema manualmente sem Alembic.
- Não usar `localStorage` como banco após a migração.
- Não avançar de fase com testes falhando.
- Não quebrar a versão web ao adicionar Capacitor.
- Não duplicar lógica de negócio no front-end e no Android; regra crítica pertence ao backend.
- Usar UTC no banco e converter para `America/Sao_Paulo` na apresentação.
- Aplicar índices e paginação desde o início.
- Garantir compatibilidade mobile-first e acessibilidade básica.

---

## 24. ENTREGÁVEIS FINAIS

Ao final, fornecer:

- código-fonte organizado;
- README completo;
- documentação de arquitetura;
- diagrama do banco;
- documentação da API;
- migrações Alembic;
- `.env.example`;
- Dockerfiles;
- Compose de desenvolvimento e produção;
- instruções EasyPanel;
- instruções DNS e domínio;
- instruções de backup e restauração;
- testes automatizados;
- relatório de testes em aparelho Android;
- APK assinado para instalação direta;
- documentação das permissões;
- manual para atualizar o APK;
- checklist de produção;
- limitações conhecidas e próximos passos.

---

## 25. REFERÊNCIAS TÉCNICAS OFICIAIS

- Repositório atual: `https://github.com/RicardovSantos/study-eneven`
- EasyPanel App Service: `https://easypanel.io/docs/services/app`
- EasyPanel Compose Service: `https://easypanel.io/docs/services/compose`
- EasyPanel PostgreSQL: `https://easypanel.io/docs/services/postgres`
- EasyPanel backups: `https://easypanel.io/docs/backups/database`
- FastAPI WebSockets: `https://fastapi.tiangolo.com/advanced/websockets/`
- FastAPI JWT e Argon2: `https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/`
- Capacitor: `https://capacitorjs.com/docs/`
- Código Android personalizado no Capacitor: `https://capacitorjs.com/docs/android/custom-code`
- Android MediaProjection: `https://developer.android.com/media/grow/media-projection`
- Android Foreground Services: `https://developer.android.com/develop/background-work/services/fgs`
- Android localização: `https://developer.android.com/develop/sensors-and-location/location/permissions`
- Android geofencing: `https://developer.android.com/develop/sensors-and-location/location/geofencing`
- Android WorkManager: `https://developer.android.com/develop/background-work/background-tasks/persistent`
- Android overlay: `https://developer.android.com/reference/android/Manifest.permission#SYSTEM_ALERT_WINDOW`

---

## 26. PRIMEIRA RESPOSTA ESPERADA DO AGENTE

Antes de escrever código, responda com:

1. resumo do entendimento;
2. inventário do repositório atual;
3. riscos encontrados;
4. arquitetura proposta;
5. plano de execução por fases;
6. decisões que precisam de confirmação;
7. comandos que serão executados na Fase 0;
8. confirmação de que nenhuma funcionalidade atual será removida sem autorização.

Depois da aprovação, iniciar apenas a Fase 0.

