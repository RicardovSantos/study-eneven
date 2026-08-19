/* Troca de tela.

   Nao conhece as paginas: so liga/desliga a classe .on das secoes e
   avisa pelo barramento. Quem desenha cada tela se inscreve em
   REDESENHAR, e o relogio flutuante em IR_PARA. */

import { $, $$ } from "./utils/dom.js";
import { E } from "./stores/app-store.js";
import { emitir, EVENTOS } from "./core/bus.js";
import { COM_SERVIDOR } from "./config.js";

export const TELAS_INTERNAS = ["home","objetivos","estudar","familia","perfil"];

let telaAtual = "login";
export const telaAgora = () => telaAtual;

/* Sem servidor, não existe conta de dependente nem painel de família —
   as abas de sempre continuam todas visíveis. Com servidor, o papel
   (sempre lido de E.papel, nunca inventado aqui) decide: só o
   responsável cadastra objetivos e vê a Família; o dependente só
   executa e acompanha o próprio progresso. */
function botaoVisivel(nomeBotao){
  if(!COM_SERVIDOR) return nomeBotao !== "familia";
  if(nomeBotao === "familia") return E.papel === "admin";
  if(nomeBotao === "objetivos") return E.papel !== "dependent";
  return true;
}

export function ir(nome){
  telaAtual = nome;
  $$(".tela").forEach(t=>t.classList.remove("on"));
  const el = $("#tela-"+nome); if(el) el.classList.add("on");
  const dentro = TELAS_INTERNAS.includes(nome);
  $("#nav").classList.toggle("on", dentro && E.logado);
  $$(".nav-btn").forEach(b=>{
    const at = b.dataset.ir===nome;
    b.classList.toggle("ativo", at);
    if(at) b.setAttribute("aria-current","page"); else b.removeAttribute("aria-current");
    b.classList.toggle("escondido", !botaoVisivel(b.dataset.ir));
  });
  $("#palco").scrollTop = 0;
  emitir(EVENTOS.REDESENHAR);
  emitir(EVENTOS.IR_PARA, nome);
}
