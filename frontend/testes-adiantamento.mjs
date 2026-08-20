/* Testes de ponta a ponta do adiantamento, num navegador de verdade:
   o formulário de objetivo passa a expor "Permite adiantar" +
   "Máximo de adiantamentos", e concluir uma tarefa hoje oferece
   adiantar a próxima quando o objetivo permite.

   Como rodar: mesmos três passos de testes-integracao.mjs (backend no
   ar + `npm run dev` com VITE_API_URL apontando pra ele), trocando o
   passo 3 por:

     node testes-adiantamento.mjs

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
await page.fill("#cad-nome", "Responsável Adianta");
await page.fill("#cad-email", `adianta${suf}@teste.com`);
await page.fill("#cad-senha", "Senha1234");
await page.fill("#cad-senha2", "Senha1234");
await page.check("#cad-termos");
await page.click("#b-criar");
await page.waitForSelector("#tela-home.on", { timeout: 8000 });
if(await page.locator("#veu.on").count()) await page.keyboard.press("Escape");

await page.click('.nav-btn[data-ir="objetivos"]');
await page.waitForSelector("#tela-objetivos.on");
await page.waitForFunction(() => getComputedStyle(document.querySelector("#campo-adianta")).display !== "none");
checar("campo de adiantamento aparece no formulário", await page.locator("#campo-adianta").isVisible());
checar("'Não permite' é o padrão", await page.locator('#p-adianta [data-v="0"]').evaluate(b => b.classList.contains("on")));

// ---- objetivo SEM permissão de adiantar: tentar adiantar não deve oferecer nada ----
await page.click('#p-tipo [data-v="tarefa"]');
await page.fill("#f-nome", "Tarefa sem adiantamento");
await page.click("#b-salvar-item");
await page.waitForSelector("#veu.on");
await page.keyboard.press("Escape");

await page.click('.nav-btn[data-ir="estudar"]');
await page.waitForSelector("#tela-estudar.on");
await page.waitForFunction(() => document.querySelector("#lista-diaria")?.textContent.includes("Tarefa sem adiantamento"));
await page.click('#lista-diaria [data-check]');
await page.waitForTimeout(1200);
checar("objetivo diário sem adiantamento não abre modal de adiantar",
  !(await page.locator("#veu.on").count()));

// ---- objetivo diário COM permissão de adiantar ----
await page.click('.nav-btn[data-ir="objetivos"]');
await page.waitForSelector("#tela-objetivos.on");
await page.click('#p-tipo [data-v="tarefa"]');
await page.fill("#f-nome", "Tarefa com adiantamento");
await page.click('#p-adianta [data-v="1"]');
await page.click("#b-salvar-item");
await page.waitForSelector("#veu.on");
await page.keyboard.press("Escape");
await page.waitForFunction(() => document.querySelector("#lista-crud")?.textContent.includes("Tarefa com adiantamento"));

// edição preserva o "Permite" selecionado
const linhaEdit = page.locator('#lista-crud .item:has-text("Tarefa com adiantamento") [data-edit]');
await linhaEdit.click();
await page.waitForFunction(() => document.querySelector("#f-nome").value === "Tarefa com adiantamento");
checar("editar objetivo pré-seleciona 'Permite adiantar'",
  await page.locator('#p-adianta [data-v="1"]').evaluate(b => b.classList.contains("on")));
await page.click("#b-cancelar-item");

await page.click('.nav-btn[data-ir="estudar"]');
await page.waitForSelector("#tela-estudar.on");
await page.waitForFunction(() => document.querySelector("#lista-diaria")?.textContent.includes("Tarefa com adiantamento"));
await page.locator('#lista-diaria .item', { hasText: "Tarefa com adiantamento" })
  .locator('[data-check]').click();
await page.waitForSelector("#veu.on", { timeout: 8000 });
const textoModal = await page.textContent("#md-titulo");
checar("modal de adiantar aparece após concluir objetivo com permissão",
  textoModal.includes("Adiantar"));

await page.click('#md-botoes button:has-text("Adiantar")');
await page.waitForTimeout(1000);
checar("sem erro de JS/API depois de confirmar o adiantamento", erros.length === 0);

checar("sem erros de JS", erros.length === 0);
if(erros.length) console.log("  erros:", erros);

await browser.close();
console.log(`\n${ok} passaram, ${falhas.length} falharam`);
if(falhas.length){ console.log("Falhas:", falhas); process.exit(1); }
