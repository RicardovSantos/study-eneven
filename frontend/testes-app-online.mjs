/* Testes de ponta a ponta do app inteiro em modo API, num navegador de
   verdade — cadastro pela tela, criar/editar objetivo, executar na tela
   Estudar, cronômetro com sessão real no servidor, gráficos da Home,
   sair e logar de novo.

   Diferença do testes-integracao.mjs: aquele exercita o cliente da API
   isolado (window.devlog.*, via integracao.html); este clica na
   interface de verdade, como um usuário faria.

   Como rodar: mesmos três passos de testes-integracao.mjs (ver o
   cabeçalho lá), trocando o passo 3 por:

     node testes-app-online.mjs

   Roda contra http://127.0.0.1:5173/ (o `npm run dev` com
   VITE_API_URL apontando para o backend). */

import { chromium } from 'playwright';
const OUT='/tmp/claude-0/-home-user/e92767e0-c85d-52db-84f8-25e2e5a6aa9f/scratchpad';
const b = await chromium.launch();
const ctx = await b.newContext({ viewport:{width:390,height:844}, deviceScaleFactor:2, isMobile:true, hasTouch:true });
const p = await ctx.newPage();
const erros=[];
p.on('pageerror', e=>erros.push('pageerror: '+e.message));
// O primeiro acesso sem cookie de sessão bate em /auth/renovar e recebe
// 401 de propósito (é a tentativa silenciosa de retomar sessão — ver
// tentarSessaoOnline()). O Chrome loga qualquer status de erro HTTP no
// console mesmo quando o JS trata a resposta corretamente; esse 401
// específico é esperado e não conta como falha real.
p.on('console', m=>{
  if(m.type()!=='error') return;
  if((m.location()?.url||'').includes('/auth/renovar')) return;
  erros.push('console: '+m.text()+' @ '+(m.location()?.url||'?'));
});

const ok=[], falhas=[];
const check=(nome,cond,extra='')=>{ (cond?ok:falhas).push(nome+(cond?'':` → ${extra}`)); };
const sufixo = Date.now().toString(36);

await p.goto('http://127.0.0.1:5173/');
await p.waitForTimeout(500);

// --- cadastro real pela tela (não pelo cliente direto: exercita o app inteiro) ---
await p.click('#b-ir-cadastro');
await p.fill('#cad-nome', 'Ricardo Vieira dos Santos');
await p.fill('#cad-email', `ricardo${sufixo}@exemplo.com`);
await p.fill('#cad-senha', 'senha1234');
await p.fill('#cad-senha2', 'senha1234');
await p.check('#cad-termos');
await p.click('#b-criar');
await p.waitForTimeout(600);
check('1 cadastro pela tela entra na Home', await p.isVisible('#tela-home'));
await p.evaluate(()=>document.querySelector('#veu .modal button.btn-cinza')?.click());
await p.waitForTimeout(300);
check('2 nome aparece na Home', (await p.textContent('#home-nome'))?.trim() === 'Ricardo Vieira dos Santos');

// --- recarregar mantém logado (sessão via cookie, sem localStorage) ---
await p.reload();
await p.waitForTimeout(700);
check('3 sessão sobrevive ao reload (cookie)', await p.isVisible('#tela-home'));

// --- criar objetivo pela tela ---
await p.click('.nav-btn[data-ir="objetivos"]');
await p.waitForTimeout(400);
await p.fill('#f-nome', 'Curso de Inglês');
await p.fill('#f-qtd', '2');
await p.click('#b-salvar-item');
await p.waitForTimeout(600);
await p.evaluate(()=>document.querySelector('#veu .modal button')?.click());
await p.waitForTimeout(300);
const itensCrud = await p.locator('#lista-crud .item').count();
check('4 objetivo aparece na lista de cadastro', itensCrud === 1, String(itensCrud));

// --- editar ---
await p.click('#lista-crud [data-edit]');
await p.waitForTimeout(300);
check('5 form carrega para edição', (await p.inputValue('#f-nome')) === 'Curso de Inglês');
await p.fill('#f-qtd', '3');
await p.click('#b-salvar-item');
await p.waitForTimeout(600);
await p.evaluate(()=>document.querySelector('#veu .modal button')?.click());
await p.waitForTimeout(300);

// --- tela Estudar mostra a ocorrência gerada ---
await p.click('.nav-btn[data-ir="estudar"]');
await p.waitForTimeout(500);
const temPlay = await p.locator('[data-play]').count();
check('6 objetivo editado aparece em Estudar', temPlay >= 1, String(temPlay));

// --- cronômetro real: abre sessão no servidor ---
await p.click('[data-play]');
await p.waitForTimeout(400);
check('7 cronômetro abre', await p.isVisible('#foco'));
await p.click('#fc-toggle');
await p.waitForTimeout(1500);
check('8 rodando mostra Pausar', (await p.textContent('#fc-legenda-toggle')) === 'Pausar');
await p.click('#fc-toggle'); // pausa
await p.waitForTimeout(300);
check('9 pausar volta pra Encerrar', (await p.textContent('#fc-legenda-sair')) === 'Encerrar');
await p.click('#fc-fechar'); // encerra (pausado -> encerra)
await p.waitForTimeout(700);
check('10 encerrar fecha o cronômetro', !(await p.isVisible('#foco')));
await p.screenshot({ path: OUT+'/online-estudar.png' });

// --- concluir manualmente com o check ---
await p.waitForTimeout(300);
const antesDoCheck = await p.locator('[data-check]').first();
if(await antesDoCheck.count()){
  await antesDoCheck.click();
  await p.waitForTimeout(600);
}
check('11 sem erro ao concluir manualmente', erros.length === 0, erros.join(' | '));

// --- Home reflete pontos/gráficos vindos da API ---
await p.click('.nav-btn[data-ir="home"]');
await p.waitForTimeout(600);
const semanaOk = await p.locator('#g-semana svg').count();
check('12 gráfico da semana desenha (dados da API)', semanaOk === 1);
await p.screenshot({ path: OUT+'/online-home.png' });

// --- sair e voltar a logar ---
await p.click('.nav-btn[data-ir="perfil"]');
await p.waitForTimeout(300);
await p.click('#b-sair');
await p.waitForTimeout(500);
check('13 sair volta ao login', await p.isVisible('#tela-login'));

await p.fill('#in-email', `ricardo${sufixo}@exemplo.com`);
await p.fill('#in-senha', 'senha1234');
await p.click('#b-entrar');
await p.waitForTimeout(600);
check('14 login de novo funciona', await p.isVisible('#tela-home'));

console.log(`\nPASSOU: ${ok.length}/${ok.length+falhas.length}`);
if(falhas.length) console.log('FALHOU:\n  - '+falhas.join('\n  - '));
console.log('ERROS DE JS:', erros.length ? '\n  '+erros.join('\n  ') : 'nenhum');
await b.close();
process.exit(falhas.length || erros.length ? 1 : 0);
