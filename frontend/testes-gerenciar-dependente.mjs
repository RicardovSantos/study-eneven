/* Testes de ponta a ponta de redefinir senha e desativar/reativar um
   dependente, na tela Família, num navegador de verdade.

   Como rodar: mesmos três passos de testes-integracao.mjs (backend no
   ar + `npm run dev` com VITE_API_URL apontando pra ele), trocando o
   passo 3 por:

     node testes-gerenciar-dependente.mjs

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
const usernameDep = `gerdep${suf}`;

// ---------- Admin cadastra dependente e mexe na conta dele ----------
{
  const { ctx, page, erros } = await novaPagina();
  await page.goto(BASE);
  await page.click("#b-ir-cadastro");
  await page.fill("#cad-nome", "Responsável Gerenciar");
  await page.fill("#cad-email", `gerenciar${suf}@teste.com`);
  await page.fill("#cad-senha", "Senha1234");
  await page.fill("#cad-senha2", "Senha1234");
  await page.check("#cad-termos");
  await page.click("#b-criar");
  await page.waitForSelector("#tela-home.on", { timeout: 8000 });
  if(await page.locator("#veu.on").count()) await page.keyboard.press("Escape");

  await page.click('.nav-btn[data-ir="familia"]');
  await page.waitForSelector("#tela-familia.on");
  await page.fill("#fam-nome", "Dependente Gerenciar");
  await page.fill("#fam-username", usernameDep);
  await page.fill("#fam-senha", "Senha1234");
  await page.click("#b-add-dependente");
  await page.waitForSelector("#veu.on");
  await page.keyboard.press("Escape");
  await page.waitForFunction(() => !document.querySelector("#lista-familia .vazio"));

  checar("dependente aparece marcado como ativo", (await page.textContent("#lista-familia")).includes("ativo"));
  checar("botão Desativar aparece para dependente ativo", await page.locator("[data-desativar]").isVisible());
  checar("botão Reativar não aparece ainda", !(await page.locator("[data-reativar]").count()));

  // ---- redefinir senha ----
  await page.click("[data-redefinir-senha]");
  await page.waitForSelector("#veu.on");
  await page.fill("#mv-senha-dep", "SenhaNova1");
  await page.click('#md-botoes button:has-text("Redefinir")');
  await page.waitForTimeout(600);
  checar("sem erro de JS ao redefinir senha", erros.length === 0);

  // ---- desativar ----
  await page.click("[data-desativar]");
  await page.waitForSelector("#veu.on");
  await page.click('#md-botoes button:has-text("Desativar")');
  await page.waitForFunction(() => document.querySelector("#lista-familia")?.textContent.includes("desativado"));
  checar("dependente aparece marcado como desativado", (await page.textContent("#lista-familia")).includes("desativado"));
  checar("botão vira Reativar", await page.locator("[data-reativar]").isVisible());

  await ctx.close();
}

// ---------- Login com a senha nova, e conta desativada bloqueia login ----------
{
  const { ctx, page, erros } = await novaPagina();
  await page.goto(BASE);
  await page.fill("#in-email", usernameDep);
  await page.fill("#in-senha", "Senha1234");   // senha ANTIGA
  await page.click("#b-entrar");
  await page.waitForTimeout(800);
  checar("senha antiga não funciona mais depois de redefinida", (await page.textContent("#erro-login")).length > 0);

  await page.fill("#in-senha", "SenhaNova1");  // senha nova, mas conta está desativada
  await page.click("#b-entrar");
  await page.waitForTimeout(800);
  checar("conta desativada não consegue entrar mesmo com a senha certa",
    (await page.textContent("#erro-login")).length > 0);

  checar("sem erros de JS", erros.length === 0);
  if(erros.length) console.log("  erros:", erros);
  await ctx.close();
}

await browser.close();
console.log(`\n${ok} passaram, ${falhas.length} falharam`);
if(falhas.length){ console.log("Falhas:", falhas); process.exit(1); }
