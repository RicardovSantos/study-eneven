# Arquitetura do front-end (Fase 1)

Estado depois da separação do arquivo único. O comportamento é o mesmo da
v1.1; o que mudou foi a organização.

## Antes e depois

| | v1.1 | v1.2 |
|---|---|---|
| Arquivos | 1 (`index.html`, 1.852 linhas) | 27 |
| CSS | 313 linhas embutidas | 6 arquivos em `src/css/` |
| JavaScript | 1.198 linhas em uma IIFE | 21 módulos ES em `src/js/` |
| Maior arquivo JS | 1.198 linhas | 217 (`app.js`) |
| Build | nenhum | Vite |

## Camadas

O fluxo de dependência é de cima para baixo. **Nenhuma camada de baixo
importa uma de cima** — é isso que mantém o grafo sem ciclos.

```text
app.js                 partida e ligação dos eventos do DOM
   │
   ├── pages/          desenham as telas (home, objetivos, estudar, perfil)
   │      │
   │      ├── components/   modal, toast, charts, floating-clock
   │      └── services/     regras de negócio (objetivos, timer)
   │                │
   │                ├── stores/    estado e persistência
   │                └── utils/     datas, formatação, DOM, imagem
   │
   ├── router.js      troca de tela
   └── core/bus.js    barramento de eventos
```

## Por que existe um barramento de eventos

As regras de negócio precisam pedir "redesenhe a tela". As telas precisam
chamar as regras de negócio. Se um importasse o outro diretamente, o grafo
teria ciclo — e um ciclo em módulos ES resulta em `undefined` na hora
errada, dependendo da ordem de avaliação.

A solução: `services/objetivos.js` emite `REDESENHAR` e não sabe quem
escuta. `pages/index.js` escuta e decide qual tela desenhar.

O mesmo vale para o cronômetro e o relógio flutuante, que também se
chamariam mutuamente:

```text
timer.js  ──emite SESSAO_MUDOU──▶  bus  ──▶  floating-clock.js
timer.js  ◀──emite ABRIR_FOCO────  bus  ◀──  floating-clock.js
```

Eventos usados: `REDESENHAR`, `IR_PARA`, `SESSAO_MUDOU`, `ABRIR_FOCO`,
`FECHAR_PIP`.

## Mapa dos arquivos

| Arquivo | Papel |
|---|---|
| `core/bus.js` | Barramento de eventos |
| `router.js` | Troca de tela e estado da navegação |
| `stores/storage.js` | Persistência (Claude storage, localStorage ou memória) |
| `stores/app-store.js` | Estado `E`, carregar, salvar, apagar |
| `services/objetivos.js` | Metas, acúmulo, virada de período, pontos, conclusão |
| `services/timer.js` | Cronômetro da sessão de foco |
| `components/modal.js` | Modal com devolução de foco |
| `components/toast.js` | Tarja de aviso |
| `components/charts.js` | Gráficos em SVG puro |
| `components/floating-clock.js` | Tarja arrastável e Picture-in-Picture |
| `pages/home.js` | Painel pessoal |
| `pages/objetivos.js` | CRUD de objetivos |
| `pages/estudar.js` | Execução das tarefas do período |
| `pages/perfil.js` | Conta e preferências |
| `pages/index.js` | Decide qual tela redesenhar |
| `auth/local-auth.js` | Login local — **provisório**, substituído na Fase 2 |
| `utils/*` | dom, dates, format, avatar, image, sound, demo, backup |

## Decisões

**Vanilla JS, sem framework.** A especificação (5.1) pede que a primeira
evolução preserve JavaScript puro. Nada aqui pede reatividade complexa.

**Gráficos em SVG puro, sem Chart.js.** São 43 linhas e cobrem os dois
casos existentes. A seção 5.1 permite mantê-los, e a alternativa custaria
~200 KB para o mesmo resultado.

**`E` continua um objeto mutável compartilhado.** Trocar por store
imutável faz sentido junto com a API, na Fase 2 — fazer as duas coisas de
uma vez tornaria impossível saber qual mudança quebrou o quê.

**`base` do Vite vem de variável de ambiente.** O mesmo build serve o
Pages de projeto (`/study-eneven/`) e o domínio próprio (`/`) da Fase 7.

## Rodar localmente

```bash
cd frontend
npm install
npm run dev      # servidor de desenvolvimento
npm run build    # gera dist/
npm run preview  # serve o dist/
```

## Publicação

`.github/workflows/deploy-pages.yml` faz o build a cada push na `main` e
publica no Pages.

**Falta uma ação manual:** em *Settings → Pages → Source*, trocar para
**GitHub Actions**. Enquanto isso não for feito, o Pages segue servindo o
`index.html` antigo da raiz — o site não quebra, só não recebe as
mudanças novas.

O `index.html` da raiz foi mantido de propósito como rede de segurança e
deve ser removido depois que a publicação por Actions estiver confirmada.
