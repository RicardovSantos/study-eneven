/* Testes de regressao do front-end.

   Cobre os 40 comportamentos que a Fase 1 nao podia quebrar. Roda contra
   qualquer URL, o que permite comparar a versao nova com a antiga:
   
     node testes-regressao.mjs http://localhost:4173/
   
   Sai com codigo 1 se algum cenario falhar ou se houver erro de JS. */

/* O Playwright não entra no package.json de propósito: instalá-lo como
   dependência faria o workflow do Pages baixar ~150 MB de navegadores a
   cada build, sem nenhum ganho para a publicação.

   Tenta o pacote local primeiro; se não houver, procura na instalação
   global. (Import de ESM não honra NODE_PATH — isso vale só para
   CommonJS —, por isso a busca é feita à mão.) */
import { execSync } from "node:child_process";

async function carregarPlaywright() {
  try {
    return await import("playwright");
  } catch {
    try {
      const global = execSync("npm root -g", { encoding: "utf8" }).trim();
      return await import(`${global}/playwright/index.mjs`);
    } catch {
      console.error(
        "Playwright não encontrado. Instale com:  npm i -g playwright"
      );
      process.exit(2);
    }
  }
}
const { chromium } = await carregarPlaywright();
const OUT = process.env.OUT || '.';
const URL = process.argv[2];
const b = await chromium.launch();
const ctx = await b.newContext({ viewport:{width:390,height:760}, deviceScaleFactor:2, isMobile:true, hasTouch:true });
const p = await ctx.newPage();
const erros=[];
p.on('pageerror', e=>erros.push('pageerror: '+e.message));
p.on('console', m=>{ if(m.type()==='error') erros.push('console: '+m.text()); });

const ok=[], falhas=[];
const check=(nome,cond)=>{ (cond?ok:falhas).push(nome); };
// fecha qualquer modal aberto, para o veu nao bloquear o proximo clique
const limparModal = async () => {
  for(let i=0;i<3;i++){
    const aberto = await p.evaluate(()=>document.querySelector('#veu')?.classList.contains('on'));
    if(!aberto) return;
    await p.evaluate(()=>document.querySelector('#veu .modal button')?.click());
    await p.waitForTimeout(200);
  }
};

await p.goto(URL);
await p.waitForTimeout(600);

// --- entrada ---
check('1 abre no login', await p.isVisible('#tela-login'));
await p.click('#b-entrar');
check('2 login sem conta avisa', (await p.textContent('#erro-login')).includes('Nenhuma conta'));

await p.click('#b-ir-cadastro');
await p.click('#b-criar');
check('3 cadastro valida nome', (await p.textContent('#erro-cadastro')).includes('nome'));
await p.fill('#cad-nome','Ricardo Vieira dos Santos');
await p.fill('#cad-email','naovale');
await p.click('#b-criar');
check('4 cadastro valida email', (await p.textContent('#erro-cadastro')).includes('inválido'));
await p.fill('#cad-email','r@r.com');
await p.fill('#cad-senha','12'); await p.fill('#cad-senha2','12');
await p.click('#b-criar');
check('5 cadastro valida senha curta', (await p.textContent('#erro-cadastro')).includes('4 caracteres'));
await p.fill('#cad-senha','1234'); await p.fill('#cad-senha2','9999');
await p.click('#b-criar');
check('6 cadastro valida senhas diferentes', (await p.textContent('#erro-cadastro')).includes('não são iguais'));
await p.fill('#cad-senha2','1234');
await p.click('#b-criar');
check('7 cadastro exige termos', (await p.textContent('#erro-cadastro')).includes('termos'));
await p.check('#cad-termos');
await p.click('#b-criar');
await p.waitForTimeout(400);
check('8 cadastro valido entra', await p.isVisible('#tela-home'));
await limparModal();

// --- persistencia ---
await p.reload(); await p.waitForTimeout(600);
check('9 continua logado apos recarregar', await p.isVisible('#tela-home'));
check('10 nome aparece na home', (await p.textContent('#home-nome')) === 'Ricardo Vieira dos Santos');

// --- dados de exemplo ---
await p.click('.nav-btn[data-ir="perfil"]'); await p.waitForTimeout(200);
await p.click('#b-demo'); await p.waitForTimeout(200);
await p.evaluate(()=>{ const bs=[...document.querySelectorAll('#veu .modal button')]; const x=bs.find(b=>/Carregar/.test(b.textContent)); if(x) x.click(); });
await p.waitForTimeout(400);
await limparModal();

// --- home e graficos ---
await p.click('.nav-btn[data-ir="home"]'); await p.waitForTimeout(400);
check('11 grafico da semana desenhou', (await p.locator('#g-semana svg').count()) === 1);
check('12 grafico do mes desenhou', (await p.locator('#g-mensal svg').count()) === 1);
check('13 barra do dia tem percentual', /%$/.test(await p.textContent('#dia-txt')));
check('14 historico mensal preenchido', (await p.locator('#tb-hist tr').count()) > 0);
check('15 placar de pontos', Number(await p.textContent('#pl-pontos')) > 0);
await p.screenshot({path: OUT+'/reg-home.png'});

// --- objetivos (CRUD) ---
await p.click('.nav-btn[data-ir="objetivos"]'); await p.waitForTimeout(300);
const antes = await p.locator('#lista-crud .item').count();
await p.click('#b-salvar-item');
check('16 CRUD valida nome vazio', (await p.textContent('#erro-form')).includes('nome'));
await p.fill('#f-nome','Curso de Teste');
await p.fill('#f-qtd','2');
await p.click('#b-salvar-item'); await p.waitForTimeout(400);
await limparModal();
const depois = await p.locator('#lista-crud .item').count();
check('17 criar objetivo aumenta a lista', depois === antes + 1);
await p.fill('#f-busca','Teste'); await p.waitForTimeout(300);
check('18 busca filtra', (await p.locator('#lista-crud .item').count()) === 1);
await p.fill('#f-busca',''); await p.waitForTimeout(300);
await limparModal();

// --- estudar + cronometro ---
await p.click('.nav-btn[data-ir="estudar"]'); await p.waitForTimeout(400);
check('19 lista de estudo tem itens', (await p.locator('[data-play]').count()) > 0);
await p.click('[data-play]'); await p.waitForTimeout(300);
check('20 cronometro abre', await p.isVisible('#foco'));
check('21 estado inicial mostra Iniciar', (await p.textContent('#fc-legenda-toggle')) === 'Iniciar');
check('22 estado inicial mostra Encerrar', (await p.textContent('#fc-legenda-sair')) === 'Encerrar');
const t0 = await p.textContent('#fc-tempo');
await p.click('#fc-toggle'); await p.waitForTimeout(1400);
const t1 = await p.textContent('#fc-tempo');
check('23 tempo corre ao iniciar', t0 !== t1);
check('24 rodando mostra Pausar', (await p.textContent('#fc-legenda-toggle')) === 'Pausar');
check('25 rodando mostra Minimizar', (await p.textContent('#fc-legenda-sair')) === 'Minimizar');
check('26 anel marca rodando', (await p.getAttribute('#fc-anel','class')).includes('rodando'));
await p.screenshot({path: OUT+'/reg-foco.png'});
await p.click('#fc-fechar'); await p.waitForTimeout(400);
check('27 minimizar fecha o foco', !(await p.isVisible('#foco')));
check('28 tarja flutuante aparece', (await p.getAttribute('#mini','class')).includes('on'));
const m0 = await p.textContent('#mini-tempo');
await p.waitForTimeout(1400);
check('29 tarja continua contando', m0 !== (await p.textContent('#mini-tempo')));
await p.screenshot({path: OUT+'/reg-mini.png'});
await p.click('#mini-abrir'); await p.waitForTimeout(400);
check('30 tocar na tarja reabre o foco', await p.isVisible('#foco'));
await p.click('#fc-toggle'); await p.waitForTimeout(300);
check('31 pausar volta para Encerrar', (await p.textContent('#fc-legenda-sair')) === 'Encerrar');
await p.click('#fc-fechar'); await p.waitForTimeout(400);
check('32 encerrar fecha o foco', !(await p.isVisible('#foco')));

// --- marcar concluido ---
await p.waitForTimeout(300);
const pontosAntes = await p.evaluate(()=>Number(document.querySelector('#pl-pontos')?.textContent||0));
await p.click('[data-check]'); await p.waitForTimeout(500);
await limparModal();
await p.click('.nav-btn[data-ir="home"]'); await p.waitForTimeout(400);
check('33 concluir soma pontos', Number(await p.textContent('#pl-pontos')) > pontosAntes);

// --- perfil ---
await p.click('.nav-btn[data-ir="perfil"]'); await p.waitForTimeout(300);
check('34 perfil carrega o nome', (await p.inputValue('#pf-nome')) === 'Ricardo Vieira dos Santos');
await p.click('#b-sair'); await p.waitForTimeout(400);
check('35 sair volta ao login', await p.isVisible('#tela-login'));
await p.fill('#in-email','r@r.com'); await p.fill('#in-senha','1234');
await p.click('#b-entrar'); await p.waitForTimeout(400);
check('36 login funciona com a conta criada', await p.isVisible('#tela-home'));

// --- interface ---
const aviso = await p.evaluate(()=>{ const cs=getComputedStyle(document.querySelector('#aviso')); return {op:cs.opacity, vis:cs.visibility}; });
check('37 tarja de aviso escondida', aviso.op === '0' && aviso.vis === 'hidden');
const pad = await p.evaluate(()=>getComputedStyle(document.querySelector('#palco')).paddingBottom);
check('38 folga inferior preservada', parseInt(pad) >= 96);
const navs = await p.$$eval('.nav-btn', bs=>bs.map(b=>b.textContent.trim()));
check('39 abas com os nomes certos', navs[0]==='Objetivos' && navs[2]==='Estudar');
const scrollX = await p.evaluate(()=>document.documentElement.scrollWidth > document.documentElement.clientWidth);
check('40 sem rolagem horizontal', !scrollX);

console.log(`\nPASSOU: ${ok.length}/${ok.length+falhas.length}`);
if(falhas.length) console.log('FALHOU:\n  - ' + falhas.join('\n  - '));
console.log('ERROS DE JS:', erros.length ? '\n  '+erros.join('\n  ') : 'nenhum');
await b.close();
process.exit(falhas.length || erros.length ? 1 : 0);
