/* Testes de ponta a ponta da tela Prêmios (trilhas de recompensa),
   num navegador de verdade: responsável cria trilha e nível, ganha
   pontos completando uma tarefa, solicita e confirma a entrega; troca
   de beneficiário sem misturar as trilhas de duas pessoas; dependente
   só enxerga o que é dele.

   Como rodar: mesmos três passos de testes-integracao.mjs (backend no
   ar + `npm run dev` com VITE_API_URL apontando pra ele), trocando o
   passo 3 por:

     node testes-recompensas.mjs

   Roda contra http://127.0.0.1:5173/, igual testes-app-online.mjs. */

import { chromium } from "playwright";

const BASE = "http://127.0.0.1:5173/";
let ok = 0, falhas = [];
function checar(nome, cond){
  if(cond){ ok++; console.log("OK  ", nome); }
  else { falhas.push(nome); console.log("FALHOU", nome); }
}

const browser = await chromium.launch();
async function novaPagina(){
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  const erros = [];
  page.on("pageerror", e => erros.push(e.message));
  page.on("console", m => { if(m.type()==="error" && !m.text().includes("Failed to load resource")) erros.push(m.text()); });
  return { ctx, page, erros };
}

const suf = Date.now().toString(36);

// ---------- Admin cadastra, cria trilha, adiciona nível ----------
{
  const { ctx, page, erros } = await novaPagina();
  await page.goto(BASE);
  await page.click("#b-ir-cadastro");
  await page.fill("#cad-nome", "Responsável Prêmios");
  await page.fill("#cad-email", `premios-admin${suf}@teste.com`);
  await page.fill("#cad-senha", "Senha1234");
  await page.fill("#cad-senha2", "Senha1234");
  await page.check("#cad-termos");
  await page.click("#b-criar");
  await page.waitForSelector("#tela-home.on", { timeout: 8000 });
  if(await page.locator("#veu.on").count()) await page.keyboard.press("Escape");

  checar("nav mostra Prêmios para admin", await page.locator('.nav-btn[data-ir="recompensas"]').isVisible());
  await page.click('.nav-btn[data-ir="recompensas"]');
  await page.waitForSelector("#tela-recompensas.on");
  // O placeholder estático já mostra "Nenhuma trilha" antes do JS rodar;
  // o sinal real de que sincronizarRecompensas()+renderRecompensas() já
  // rodaram é o form (escondido por padrão no HTML) ter sido revelado.
  await page.waitForFunction(() => getComputedStyle(document.querySelector("#rec-nova-trilha")).display !== "none");
  checar("lista de trilhas começa vazia", (await page.textContent("#lista-trilhas")).includes("Nenhuma trilha"));
  checar("form de nova trilha visível para admin", await page.locator("#rec-nova-trilha").isVisible());

  await page.fill("#rec-trilha-nome", "Trilha Geral");
  await page.click("#b-criar-trilha");
  await page.waitForFunction(() => !document.querySelector("#lista-trilhas .vazio"));
  checar("trilha criada aparece na lista", (await page.textContent("#lista-trilhas")).includes("Trilha Geral"));

  await page.click('[data-add-nivel]');
  await page.waitForSelector("#veu.on");
  await page.fill("#mv-pontos", "5");
  await page.fill("#mv-premio", "Uma sobremesa");
  await page.click('#md-botoes button:has-text("Adicionar")');
  await page.waitForSelector("#veu.on", { state: "hidden" }).catch(()=>{});
  await page.waitForFunction(() => document.querySelector("#lista-trilhas")?.textContent.includes("Faltam"));
  checar("meta do próximo nível aparece na trilha", (await page.textContent("#lista-trilhas")).includes("Uma sobremesa"));

  // ---- ganha os 5 pontos completando uma tarefa, depois solicita e entrega o prêmio ----
  await page.click('.nav-btn[data-ir="objetivos"]');
  await page.waitForSelector("#tela-objetivos.on");
  await page.click('#p-tipo [data-v="tarefa"]');
  await page.fill("#f-nome", "Tarefa Teste");
  await page.click("#b-salvar-item");
  await page.waitForSelector("#veu.on");
  await page.keyboard.press("Escape");

  await page.click('.nav-btn[data-ir="estudar"]');
  await page.waitForSelector("#tela-estudar.on");
  await page.waitForFunction(() => document.querySelector("#lista-diaria")?.textContent.includes("Tarefa Teste"));
  await page.click('#lista-diaria [data-check]');
  await page.waitForTimeout(600);

  await page.click('.nav-btn[data-ir="recompensas"]');
  await page.waitForSelector("#tela-recompensas.on");
  await page.waitForFunction(() => document.querySelector("#lista-premios")?.textContent.includes("Uma sobremesa"), { timeout: 8000 });
  checar("prêmio aparece desbloqueado após ganhar os pontos",
    (await page.textContent("#lista-premios")).includes("Desbloqueado"));

  await page.click('[data-solicitar]');
  await page.waitForFunction(() => document.querySelector("#lista-premios")?.textContent.includes("Pedido"));
  checar("prêmio muda para 'Pedido' após solicitar", (await page.textContent("#lista-premios")).includes("Pedido"));

  await page.click('[data-entregar]');
  await page.waitForFunction(() => document.querySelector("#lista-premios")?.textContent.includes("Entregue"));
  checar("prêmio muda para 'Entregue' após confirmar", (await page.textContent("#lista-premios")).includes("Entregue"));

  checar("sem erros de JS (fluxo trilha)", erros.length === 0);
  if(erros.length) console.log("  erros:", erros);
  await ctx.close();
}

// ---------- Dependente vê só suas próprias trilhas/prêmios ----------
{
  const { ctx: ctxAdmin, page: pageAdmin } = await novaPagina();
  await pageAdmin.goto(BASE);
  await pageAdmin.click("#b-ir-cadastro");
  await pageAdmin.fill("#cad-nome", "Responsável Dois");
  await pageAdmin.fill("#cad-email", `premios-admin2${suf}@teste.com`);
  await pageAdmin.fill("#cad-senha", "Senha1234");
  await pageAdmin.fill("#cad-senha2", "Senha1234");
  await pageAdmin.check("#cad-termos");
  await pageAdmin.click("#b-criar");
  await pageAdmin.waitForSelector("#tela-home.on", { timeout: 8000 });
  if(await pageAdmin.locator("#veu.on").count()) await pageAdmin.keyboard.press("Escape");

  const usernameDep = `depprem${suf}`;
  await pageAdmin.click('.nav-btn[data-ir="familia"]');
  await pageAdmin.waitForSelector("#tela-familia.on");
  await pageAdmin.fill("#fam-nome", "Dependente Prêmios");
  await pageAdmin.fill("#fam-username", usernameDep);
  await pageAdmin.fill("#fam-senha", "Senha1234");
  await pageAdmin.click("#b-add-dependente");
  await pageAdmin.waitForSelector("#veu.on");
  await pageAdmin.keyboard.press("Escape");

  await pageAdmin.click('.nav-btn[data-ir="recompensas"]');
  await pageAdmin.waitForSelector("#tela-recompensas.on");
  await pageAdmin.waitForSelector("#rec-quem .pill", { timeout: 8000 });
  checar("seletor 'de quem' aparece quando há dependente", await pageAdmin.locator("#rec-card-quem").isVisible());

  // Cria uma trilha para SI MESMO, depois troca pro dependente e cria
  // outra — as duas não podem se misturar.
  await pageAdmin.fill("#rec-trilha-nome", "Trilha do Admin");
  await pageAdmin.click("#b-criar-trilha");
  await pageAdmin.waitForFunction(() => document.querySelector("#lista-trilhas")?.textContent.includes("Trilha do Admin"));

  await pageAdmin.click('[data-quem]:has-text("Dependente Prêmios")');
  await pageAdmin.waitForFunction(() => !document.querySelector("#lista-trilhas")?.textContent.includes("Trilha do Admin"));
  checar("trocar de beneficiário troca a lista de trilhas",
    (await pageAdmin.textContent("#lista-trilhas")).includes("Nenhuma trilha"));

  await pageAdmin.fill("#rec-trilha-nome", "Trilha do Dependente");
  await pageAdmin.click("#b-criar-trilha");
  await pageAdmin.waitForFunction(() => document.querySelector("#lista-trilhas")?.textContent.includes("Trilha do Dependente"));

  await pageAdmin.click('[data-quem]:has-text("Eu mesmo")');
  await pageAdmin.waitForFunction(() => document.querySelector("#lista-trilhas")?.textContent.includes("Trilha do Admin"));
  checar("voltar para 'Eu mesmo' não mostra a trilha do dependente",
    !(await pageAdmin.textContent("#lista-trilhas")).includes("Trilha do Dependente"));

  await ctxAdmin.close();

  const { ctx, page, erros } = await novaPagina();
  await page.goto(BASE);
  await page.fill("#in-email", usernameDep);
  await page.fill("#in-senha", "Senha1234");
  await page.click("#b-entrar");
  await page.waitForSelector("#tela-home.on", { timeout: 8000 });
  checar("nav mostra Prêmios para dependente", await page.locator('.nav-btn[data-ir="recompensas"]').isVisible());
  await page.click('.nav-btn[data-ir="recompensas"]');
  await page.waitForSelector("#tela-recompensas.on");
  checar("seletor 'de quem' não aparece para dependente", !(await page.locator("#rec-card-quem").isVisible()));
  await page.waitForFunction(() => document.querySelector("#lista-trilhas")?.textContent.includes("Trilha do Dependente"));
  checar("form de nova trilha escondido para dependente", !(await page.locator("#rec-nova-trilha").isVisible()));
  checar("dependente vê a trilha que o responsável criou para ele",
    (await page.textContent("#lista-trilhas")).includes("Trilha do Dependente"));
  checar("dependente NÃO vê a trilha do responsável",
    !(await page.textContent("#lista-trilhas")).includes("Trilha do Admin"));

  checar("sem erros de JS (fluxo dependente)", erros.length === 0);
  if(erros.length) console.log("  erros:", erros);
  await ctx.close();
}

await browser.close();
console.log(`\n${ok} passaram, ${falhas.length} falharam`);
if(falhas.length){ console.log("Falhas:", falhas); process.exit(1); }
