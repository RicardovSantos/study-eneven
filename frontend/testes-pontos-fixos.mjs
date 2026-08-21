/* Testes de ponta a ponta dos pontos fixos de tarefa no formulário de
   objetivo, num navegador de verdade: o campo só aparece pra tarefa em
   modo servidor, o padrão é 5, editar preserva o valor salvo, e
   concluir a tarefa credita exatamente os pontos configurados.

   Como rodar: mesmos três passos de testes-integracao.mjs (backend no
   ar + `npm run dev` com VITE_API_URL apontando pra ele), trocando o
   passo 3 por:

     node testes-pontos-fixos.mjs

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
await page.fill("#cad-nome", "Responsável Pontos");
await page.fill("#cad-email", `pontosfixos${suf}@teste.com`);
await page.fill("#cad-senha", "Senha1234");
await page.fill("#cad-senha2", "Senha1234");
await page.check("#cad-termos");
await page.click("#b-criar");
await page.waitForSelector("#tela-home.on", { timeout: 8000 });
if(await page.locator("#veu.on").count()) await page.keyboard.press("Escape");

await page.click('.nav-btn[data-ir="objetivos"]');
await page.waitForSelector("#tela-objetivos.on");
await page.waitForFunction(() => getComputedStyle(document.querySelector("#campo-adianta")).display !== "none");

checar("campo de pontos fixos escondido para estudo (tipo padrão)",
  !(await page.locator("#campo-pontos-fixos").isVisible()));

await page.click('#p-tipo [data-v="tarefa"]');
checar("campo de pontos fixos aparece ao trocar para tarefa",
  await page.locator("#campo-pontos-fixos").isVisible());
checar("valor padrão é 5", await page.inputValue("#f-pontos-fixos") === "5");

await page.click('#p-tipo [data-v="estudo"]');
checar("campo some de novo ao voltar pra estudo",
  !(await page.locator("#campo-pontos-fixos").isVisible()));

// ---- cria uma tarefa com 20 pontos e confere que credita exatamente isso ----
await page.click('#p-tipo [data-v="tarefa"]');
await page.fill("#f-nome", "Tarefa 20 pontos");
await page.fill("#f-pontos-fixos", "20");
await page.click("#b-salvar-item");
await page.waitForSelector("#veu.on");
await page.keyboard.press("Escape");
await page.waitForFunction(() => document.querySelector("#lista-crud")?.textContent.includes("Tarefa 20 pontos"));

// edição preserva o valor salvo
const linhaEdit = page.locator('#lista-crud .item:has-text("Tarefa 20 pontos") [data-edit]');
await linhaEdit.click();
await page.waitForFunction(() => document.querySelector("#f-nome").value === "Tarefa 20 pontos");
checar("editar objetivo pré-preenche os pontos fixos salvos",
  await page.inputValue("#f-pontos-fixos") === "20");
await page.click("#b-cancelar-item");

await page.click('.nav-btn[data-ir="estudar"]');
await page.waitForSelector("#tela-estudar.on");
await page.waitForFunction(() => document.querySelector("#lista-diaria")?.textContent.includes("Tarefa 20 pontos"));
await page.locator('#lista-diaria .item', { hasText: "Tarefa 20 pontos" }).locator('[data-check]').click();
await page.waitForSelector("#aviso.on", { timeout: 8000 }).catch(()=>{});
await page.waitForTimeout(500);
checar("mensagem de conclusão mostra os 20 pontos configurados",
  (await page.textContent("#aviso")).includes("+20"));

checar("sem erros de JS", erros.length === 0);
if(erros.length) console.log("  erros:", erros);

await browser.close();
console.log(`\n${ok} passaram, ${falhas.length} falharam`);
if(falhas.length){ console.log("Falhas:", falhas); process.exit(1); }
