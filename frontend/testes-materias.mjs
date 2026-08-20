/* Testes de ponta a ponta do CRUD de matérias, num navegador de
   verdade: cadastrar objetivo sem matéria (continua "Sem matéria"),
   criar matéria, associar a um objetivo, ver o nome aparecer nas
   telas Objetivos e Estudar, renomear e arquivar.

   Como rodar: mesmos três passos de testes-integracao.mjs (backend no
   ar + `npm run dev` com VITE_API_URL apontando pra ele), trocando o
   passo 3 por:

     node testes-materias.mjs

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
await page.fill("#cad-nome", "Responsável Matérias");
await page.fill("#cad-email", `materias-admin${suf}@teste.com`);
await page.fill("#cad-senha", "Senha1234");
await page.fill("#cad-senha2", "Senha1234");
await page.check("#cad-termos");
await page.click("#b-criar");
await page.waitForSelector("#tela-home.on", { timeout: 8000 });
if(await page.locator("#veu.on").count()) await page.keyboard.press("Escape");

await page.click('.nav-btn[data-ir="objetivos"]');
await page.waitForSelector("#tela-objetivos.on");
await page.waitForFunction(() => getComputedStyle(document.querySelector("#card-materias")).display !== "none");
checar("card de matérias aparece para admin", await page.locator("#card-materias").isVisible());
checar("lista de matérias começa vazia", (await page.textContent("#lista-materias")).includes("Nenhuma matéria"));

// ---- objetivo sem matéria continua "Sem matéria" ----
await page.fill("#f-nome", "Curso sem matéria");
await page.click("#b-salvar-item");
await page.waitForSelector("#veu.on");
await page.keyboard.press("Escape");
await page.waitForFunction(() => document.querySelector("#lista-crud")?.textContent.includes("Curso sem matéria"));
checar("objetivo sem matéria mostra 'Sem matéria'",
  (await page.textContent("#lista-crud")).includes("Sem matéria"));

// ---- cria matéria ----
await page.fill("#materia-nome", "Inglês");
await page.click("#b-criar-materia");
await page.waitForFunction(() => document.querySelector("#lista-materias")?.textContent.includes("Inglês"));
checar("matéria criada aparece na lista", (await page.textContent("#lista-materias")).includes("Inglês"));
checar("matéria criada aparece no select do formulário",
  await page.locator("#f-cat option", { hasText: "Inglês" }).count() === 1);

// ---- cria objetivo com matéria ----
await page.click("#b-cancelar-item");
await page.fill("#f-nome", "Curso de Inglês");
await page.selectOption("#f-cat", { label: "Inglês" });
await page.click("#b-salvar-item");
await page.waitForSelector("#veu.on");
await page.keyboard.press("Escape");
await page.waitForFunction(() => {
  const linhas = [...document.querySelectorAll("#lista-crud .item")];
  return linhas.some(l => l.textContent.includes("Curso de Inglês") && l.textContent.includes("Inglês"));
});
checar("objetivo com matéria mostra o nome da matéria", true);

// ---- aparece também na tela Estudar ----
await page.click('.nav-btn[data-ir="estudar"]');
await page.waitForSelector("#tela-estudar.on");
await page.waitForFunction(() => document.querySelector("#lista-diaria")?.textContent.includes("Curso de Inglês"));
checar("tela Estudar também mostra o nome da matéria",
  (await page.textContent("#lista-diaria")).includes("Inglês"));

// ---- editar objetivo preserva a matéria selecionada ----
await page.click('.nav-btn[data-ir="objetivos"]');
await page.waitForSelector("#tela-objetivos.on");
await page.waitForFunction(() => document.querySelector("#lista-crud")?.textContent.includes("Curso de Inglês"));
const linhaInglesEdit = page.locator('#lista-crud .item:has-text("Curso de Inglês") [data-edit]');
await linhaInglesEdit.click();
await page.waitForFunction(() => document.querySelector("#f-nome").value === "Curso de Inglês");
checar("editar objetivo pré-seleciona a matéria certa",
  await page.locator("#f-cat option:checked").innerText() === "Inglês");
await page.click("#b-cancelar-item");

// ---- renomear matéria ----
await page.click('[data-edit-materia]');
await page.waitForSelector("#veu.on");
await page.fill("#mv-materia-nome", "Inglês Avançado");
await page.click('#md-botoes button:has-text("Salvar")');
await page.waitForFunction(() => document.querySelector("#lista-materias")?.textContent.includes("Inglês Avançado"));
checar("matéria renomeada aparece na lista", (await page.textContent("#lista-materias")).includes("Inglês Avançado"));
await page.waitForFunction(() => {
  const linhas = [...document.querySelectorAll("#lista-crud .item")];
  return linhas.some(l => l.textContent.includes("Curso de Inglês") && l.textContent.includes("Inglês Avançado"));
});
checar("renomear matéria atualiza o nome no objetivo já cadastrado", true);

// ---- arquivar matéria ----
await page.click('[data-del-materia]');
await page.waitForSelector("#veu.on");
await page.click('#md-botoes button:has-text("Arquivar")');
await page.waitForFunction(() => document.querySelector("#lista-materias")?.textContent.includes("Nenhuma matéria"));
checar("matéria arquivada some da lista", (await page.textContent("#lista-materias")).includes("Nenhuma matéria"));
checar("matéria arquivada some do select do formulário",
  await page.locator("#f-cat option", { hasText: "Inglês Avançado" }).count() === 0);
checar("objetivo com matéria arquivada volta a mostrar 'Sem matéria'",
  (await page.textContent("#lista-crud")).includes("Sem matéria"));

checar("sem erros de JS", erros.length === 0);
if(erros.length) console.log("  erros:", erros);

await browser.close();
console.log(`\n${ok} passaram, ${falhas.length} falharam`);
if(falhas.length){ console.log("Falhas:", falhas); process.exit(1); }
