/* Testes de integração do cliente da API, num navegador de verdade.

   Provam o que um teste em Node não consegue: fetch real, CORS real,
   cookie HttpOnly real, e a renovação automática do token disparada por
   um 401 de verdade.

   Como rodar (três terminais, ou em segundo plano):

     1) backend:  cd backend && DATABASE_URL="sqlite+aiosqlite:///./dev.db" \
                  JWT_SECRET_KEY="…32+ caracteres…" \
                  CORS_ORIGINS="http://127.0.0.1:5173" \
                  uvicorn app.main:app --port 8000
     2) front:    cd frontend && VITE_API_URL=http://127.0.0.1:8000 npm run dev
     3) testes:   node testes-integracao.mjs

   Atenção ao CORS: para o navegador, 127.0.0.1 e localhost são origens
   diferentes. Autorizar só uma das duas faz toda chamada falhar com
   "Failed to fetch", sem pista nenhuma no console. */

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
const b = await chromium.launch();
const p = await (await b.newContext()).newPage();
const erros = [];
p.on('pageerror', e => erros.push(e.message));
await p.goto('http://127.0.0.1:5173/integracao.html');
await p.waitForFunction(() => !!window.devlog);

const ok = [], falhas = [];
const check = (nome, cond, extra='') => (cond ? ok : falhas).push(nome + (cond ? '' : ` → ${extra}`));

const cfg = await p.evaluate(() => ({ url: window.devlog.API_URL, com: window.devlog.COM_SERVIDOR }));
check('1 config lê VITE_API_URL', cfg.url === 'http://127.0.0.1:8000', cfg.url);
check('2 detecta que há servidor', cfg.com === true);

const sufixo = Date.now().toString(36);

// cadastro real
const cad = await p.evaluate(async (s) => {
  try {
    const r = await window.devlog.auth.cadastrar({
      nome: 'Ricardo Vieira dos Santos', email: `r${s}@exemplo.com`,
      senha: 'senha1234', username: `ricardo${s}`, nomeFamilia: 'Santos',
    });
    return { ok: true, papel: r.papel, nome: r.usuario.nome_exibicao, temToken: window.devlog.temToken() };
  } catch (e) { return { ok: false, erro: e.message }; }
}, sufixo);
check('3 cadastro pela API', cad.ok && cad.papel === 'admin', cad.erro);
check('4 token fica em memória', cad.temToken === true);
check('5 usuário volta correto', cad.nome === 'Ricardo Vieira dos Santos');

// cookie HttpOnly de refresh
const cookies = await p.context().cookies();
const refresh = cookies.find(c => c.name === 'devlog_refresh');
check('6 cookie de refresh existe', !!refresh);
check('7 cookie é HttpOnly', refresh?.httpOnly === true);

// o token NÃO pode estar acessível ao JavaScript
const vazou = await p.evaluate(() => document.cookie.includes('devlog_refresh'));
check('8 refresh fora do alcance do JS', vazou === false);

// criar objetivo
const obj = await p.evaluate(async () => {
  try {
    const o = await window.devlog.objetivos.criar({
      tipo: 'study', nome: 'Curso de Inglês', meta_periodo: 40,
      frequencia: 'daily', permite_adiantar: true, max_adiantamentos: 1,
    });
    const ocs = await window.devlog.objetivos.ocorrencias();
    return { ok: true, id: o.id, quantas: ocs.length, primeira: ocs[0]?.id };
  } catch (e) { return { ok: false, erro: e.message }; }
});
check('9 cria objetivo', obj.ok, obj.erro);
check('10 agenda materializada', obj.quantas >= 1, `${obj.quantas} ocorrências`);

// validação: erro 422 vira mensagem legível
const invalido = await p.evaluate(async () => {
  try {
    await window.devlog.objetivos.criar({ tipo: 'task', nome: 'Sem pontos', meta_periodo: 5, frequencia: 'monthly' });
    return { recusou: false };
  } catch (e) { return { recusou: true, status: e.status, msg: e.message }; }
});
check('11 recusa tarefa sem pontos fixos', invalido.recusou && invalido.status === 422, JSON.stringify(invalido));
check('12 mensagem de erro é legível', /pontos_fixos/.test(invalido.msg || ''), invalido.msg);

// sessão de estudo com heartbeat
const ses = await p.evaluate(async (ocId) => {
  try {
    const s = await window.devlog.sessoes.abrir({ objetivo_id: null, ocorrencia_id: ocId });
    return { ok: true };
  } catch (e) { return { ok: false, erro: e.message, status: e.status }; }
}, obj.primeira);
check('13 sessão sem objetivo_id é recusada', ses.ok === false && ses.status === 422, JSON.stringify(ses));

const ses2 = await p.evaluate(async ({ objId, ocId }) => {
  try {
    const s = await window.devlog.sessoes.abrir({ objetivo_id: objId, ocorrencia_id: ocId });
    const h = await window.devlog.sessoes.heartbeat(s.id);
    const aberta = await window.devlog.sessoes.aberta();
    const f = await window.devlog.sessoes.finalizar(s.id, { resumo: 'Revisei verbos.' });
    return { ok: true, estadoInicial: s.estado, creditou: h.segundos_creditados,
             reencontrou: aberta?.id === s.id, estadoFinal: f.sessao.estado };
  } catch (e) { return { ok: false, erro: e.message }; }
}, { objId: obj.id, ocId: obj.primeira });
check('14 abre sessão', ses2.ok && ses2.estadoInicial === 'active', ses2.erro);
check('15 heartbeat responde', typeof ses2.creditou === 'number');
check('16 sessão aberta é reencontrada', ses2.reencontrou === true);
check('17 finaliza sessão', ses2.estadoFinal === 'finished');

// painel
const pnl = await p.evaluate(async () => {
  try {
    const d = await window.devlog.painel.pessoal();
    return { ok: true, semana: Object.keys(d.serie_semana).length, temResumo: !!d.resumo };
  } catch (e) { return { ok: false, erro: e.message }; }
});
check('18 painel responde', pnl.ok, pnl.erro);
check('19 série da semana com 7 dias', pnl.semana === 7, String(pnl.semana));

// renovação automática: descarta o token e faz uma chamada
const auto = await p.evaluate(async () => {
  window.devlog.definirToken('token-invalido-de-proposito');
  try {
    const u = await window.devlog.auth.eu();
    return { ok: true, username: u.username };
  } catch (e) { return { ok: false, erro: e.message }; }
});
check('20 renova o token sozinho após 401', auto.ok, auto.erro);

// renovações simultâneas não devem se invalidar
const simultaneo = await p.evaluate(async () => {
  window.devlog.definirToken('outro-token-invalido');
  const r = await Promise.all([
    window.devlog.auth.eu(), window.devlog.auth.eu(), window.devlog.auth.eu(),
  ]).then(() => true).catch((e) => e.message);
  return r;
});
check('21 renovações simultâneas não se atropelam', simultaneo === true, String(simultaneo));

// sair invalida
const saiu = await p.evaluate(async () => {
  try { await window.devlog.auth.sair(); }
  catch (e) { return { protegido: false, erroAoSair: e.message }; }
  try { await window.devlog.auth.eu(); return { protegido: false }; }
  catch (e) { return { protegido: true, status: e.status }; }
});
check('22 sair encerra a sessão', saiu.protegido && saiu.status === 401, JSON.stringify(saiu));

console.log(`\nPASSOU: ${ok.length}/${ok.length + falhas.length}`);
if (falhas.length) console.log('FALHOU:\n  - ' + falhas.join('\n  - '));
console.log('ERROS DE JS:', erros.length ? erros.join(' | ') : 'nenhum');
await b.close();
process.exit(falhas.length ? 1 : 0);
