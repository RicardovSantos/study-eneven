/* Testes de ponta a ponta de editar o próprio perfil (nome, e-mail,
   senha), num navegador de verdade — o formulário é o mesmo do modo
   local, mas os campos que não existem no servidor (nascimento, sexo,
   escola, país, termos) somem, e "senha atual" aparece.

   Como rodar: mesmos três passos de testes-integracao.mjs (backend no
   ar + `npm run dev` com VITE_API_URL apontando pra ele), trocando o
   passo 3 por:

     node testes-perfil.mjs

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
const email = `perfil${suf}@teste.com`;

await page.goto(BASE);
await page.click("#b-ir-cadastro");
await page.fill("#cad-nome", "Nome Original");
await page.fill("#cad-email", email);
await page.fill("#cad-senha", "Senha1234");
await page.fill("#cad-senha2", "Senha1234");
await page.check("#cad-termos");
await page.click("#b-criar");
await page.waitForSelector("#tela-home.on", { timeout: 8000 });
if(await page.locator("#veu.on").count()) await page.keyboard.press("Escape");

await page.click('.nav-btn[data-ir="perfil"]');
await page.waitForSelector("#tela-perfil.on");
await page.waitForFunction(() => getComputedStyle(document.querySelector("#campo-senha-atual")).display !== "none");

checar("campo 'senha atual' aparece em modo servidor", await page.locator("#campo-senha-atual").isVisible());
checar("campos só-locais (nascimento etc.) somem em modo servidor",
  !(await page.locator("#campo-perfil-local").isVisible()));
checar("nome vem pré-preenchido", await page.inputValue("#pf-nome") === "Nome Original");
checar("email vem pré-preenchido", await page.inputValue("#pf-email") === email);

// ---- trocar nome e e-mail, sem mexer na senha ----
const novoEmail = `perfil-novo${suf}@teste.com`;
await page.fill("#pf-nome", "Nome Editado");
await page.fill("#pf-email", novoEmail);
await page.click("#b-salvar-perfil");
await page.waitForSelector("#veu.on");
await page.keyboard.press("Escape");
checar("nome exibido na Home reflete a edição", true);
await page.click('.nav-btn[data-ir="home"]');
await page.waitForSelector("#tela-home.on");
await page.waitForFunction(() => document.querySelector("#home-nome")?.textContent.includes("Nome Editado"));
checar("Home mostra o nome atualizado", (await page.textContent("#home-nome")).includes("Nome Editado"));

// ---- trocar a senha exige a atual ----
await page.click('.nav-btn[data-ir="perfil"]');
await page.waitForSelector("#tela-perfil.on");
await page.fill("#pf-senha", "SenhaNova1");
await page.click("#b-salvar-perfil");
await page.waitForTimeout(500);
checar("trocar senha sem informar a atual mostra erro e não abre modal de sucesso",
  (await page.textContent("#erro-perfil")).length > 0 && !(await page.locator("#veu.on").count()));

await page.fill("#pf-senha-atual", "Senha1234");
await page.click("#b-salvar-perfil");
await page.waitForSelector("#veu.on");
await page.keyboard.press("Escape");

// ---- login com a senha nova ----
await page.click('.nav-btn[data-ir="perfil"]');
await page.waitForSelector("#tela-perfil.on");
await page.click("#b-sair");
await page.waitForSelector("#tela-login.on", { timeout: 8000 });
await page.fill("#in-email", novoEmail);
await page.fill("#in-senha", "SenhaNova1");
await page.click("#b-entrar");
await page.waitForSelector("#tela-home.on", { timeout: 8000 });
checar("login funciona com o e-mail e a senha novos", true);

checar("sem erros de JS", erros.length === 0);
if(erros.length) console.log("  erros:", erros);

await browser.close();
console.log(`\n${ok} passaram, ${falhas.length} falharam`);
if(falhas.length){ console.log("Falhas:", falhas); process.exit(1); }
