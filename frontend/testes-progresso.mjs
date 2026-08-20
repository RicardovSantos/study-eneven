/* Testes de ponta a ponta do card "Histórico recente" na Home: some
   sem atividade, mostra os lançamentos de pontos após completar uma
   tarefa e pagina com "Carregar mais".

   Como rodar: mesmos três passos de testes-integracao.mjs (backend no
   ar + `npm run dev` com VITE_API_URL apontando pra ele), trocando o
   passo 3 por:

     node testes-progresso.mjs

   Roda contra http://127.0.0.1:5173/, igual testes-app-online.mjs. */

import { chromium } from "playwright";

const BASE = "http://127.0.0.1:5173/";
let ok = 0, falhas = [];
function checar(nome, cond){
  if(cond){ ok++; console.log("OK  ", nome); }
  else { falhas.push(nome); console.log("FALHOU", nome); }
}

const browser = await chromium.launch();
const ctx = await browser.newContext();
const page = await ctx.newPage();
const erros = [];
page.on("pageerror", e => erros.push(e.message));
page.on("console", m => { if(m.type()==="error" && !m.text().includes("Failed to load resource")) erros.push(m.text()); });

const suf = Date.now().toString(36);

await page.goto(BASE);
await page.click("#b-ir-cadastro");
await page.fill("#cad-nome", "Responsável Progresso");
await page.fill("#cad-email", `progresso${suf}@teste.com`);
await page.fill("#cad-senha", "Senha1234");
await page.fill("#cad-senha2", "Senha1234");
await page.check("#cad-termos");
await page.click("#b-criar");
await page.waitForSelector("#tela-home.on", { timeout: 8000 });
if(await page.locator("#veu.on").count()) await page.keyboard.press("Escape");

await page.waitForFunction(() => getComputedStyle(document.querySelector("#card-progresso")).display !== "none");
checar("card de histórico aparece na Home", await page.locator("#card-progresso").isVisible());
checar("histórico começa vazio", (await page.textContent("#lista-progresso")).includes("Sem atividades"));
checar("botão 'Carregar mais' escondido sem histórico",
  !(await page.locator("#b-mais-historico").isVisible()));

// ---- ganha pontos completando 12 tarefas (mais que uma página de 10) ----
await page.click('.nav-btn[data-ir="objetivos"]');
await page.waitForSelector("#tela-objetivos.on");
for(let i=1;i<=12;i++){
  await page.click('#p-tipo [data-v="tarefa"]');
  await page.fill("#f-nome", "Tarefa "+i);
  await page.click("#b-salvar-item");
  await page.waitForSelector("#veu.on");
  await page.keyboard.press("Escape");
}

await page.click('.nav-btn[data-ir="estudar"]');
await page.waitForSelector("#tela-estudar.on");
await page.waitForFunction(() => document.querySelectorAll("#lista-diaria [data-check]").length === 12);
const checks = await page.locator("#lista-diaria [data-check]").all();
for(const c of checks){
  await c.click();
  await page.waitForTimeout(300);
}

await page.click('.nav-btn[data-ir="home"]');
await page.waitForSelector("#tela-home.on");
await page.waitForFunction(() => document.querySelectorAll("#lista-progresso .item").length === 10, { timeout: 10000 });
checar("histórico mostra a primeira página (10 itens)",
  (await page.locator("#lista-progresso .item").count()) === 10);
checar("item do histórico mostra o nome da tarefa",
  (await page.textContent("#lista-progresso")).includes("Tarefa"));
checar("item do histórico mostra os pontos ganhos",
  (await page.textContent("#lista-progresso")).includes("+5"));
checar("botão 'Carregar mais' aparece com mais de uma página",
  await page.locator("#b-mais-historico").isVisible());

await page.click("#b-mais-historico");
await page.waitForFunction(() => document.querySelectorAll("#lista-progresso .item").length === 12);
checar("'Carregar mais' acrescenta o resto (12 itens)",
  (await page.locator("#lista-progresso .item").count()) === 12);
checar("botão 'Carregar mais' some quando não há mais páginas",
  !(await page.locator("#b-mais-historico").isVisible()));

checar("sem erros de JS", erros.length === 0);
if(erros.length) console.log("  erros:", erros);

await browser.close();
console.log(`\n${ok} passaram, ${falhas.length} falharam`);
if(falhas.length){ console.log("Falhas:", falhas); process.exit(1); }
