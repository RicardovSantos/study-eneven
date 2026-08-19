/* Tela Família: só o responsável vê (nav já esconde para dependente —
   ver router.js). Lista os dependentes com um resumo do progresso de
   cada um e permite cadastrar um novo.

   Tela só existe em modo servidor: sem backend não há conta de
   dependente para gerenciar (ver router.js, botaoVisivel). */

import { $ } from "../utils/dom.js";
import { E } from "../stores/app-store.js";
import { esc, fmtHM } from "../utils/format.js";

export function renderFamilia(){
  const dependentes = E.familiaDependentes || [];
  if(!dependentes.length){
    $("#lista-familia").innerHTML = '<p class="vazio">Nenhum dependente cadastrado ainda.</p>';
    return;
  }
  $("#lista-familia").innerHTML = dependentes.map(d => (
    '<div class="item">'+
      '<div class="info"><div class="nome">'+esc(d.nome)+'</div>'+
      '<div class="sub">'+fmtHM(d.minutos_hoje)+' hoje · '+d.concluidas_hoje+' concluído(s) hoje · '+
        d.pontos_totais+' ponto(s) · sequência de '+d.sequencia_dias+' dia(s)</div></div>'+
    '</div>'
  )).join("");
}
