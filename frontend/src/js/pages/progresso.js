/* Card "Histórico recente" na Home: lançamentos de pontos, mais
   recente primeiro, com paginação simples ("Carregar mais").

   Só existe em modo servidor — sem servidor os pontos não têm um
   registro individual por lançamento, só o agregado por dia em E.hist
   (a tabela "Histórico mensal" já cobre isso). */

import { $ } from "../utils/dom.js";
import { E } from "../stores/app-store.js";
import { esc } from "../utils/format.js";
import { p2 } from "../utils/dates.js";

const ROTULO_ORIGEM = {
  study_session: "sessão de estudo", task: "tarefa concluída", admin_adjustment: "ajuste",
};

function fmtQuando(iso){
  const d = new Date(iso);
  return p2(d.getDate())+"/"+p2(d.getMonth()+1)+" às "+p2(d.getHours())+":"+p2(d.getMinutes());
}

export function renderProgresso(){
  $("#card-progresso").style.display = "";

  const itens = E.historico || [];
  $("#lista-progresso").innerHTML = itens.length
    ? itens.map(i => {
        const rotulo = ROTULO_ORIGEM[i.origem] || i.origem;
        const detalhe = i.objetivo ? esc(i.objetivo) : esc(i.descricao || rotulo);
        return '<div class="item">'+
          '<div class="info"><div class="nome">'+detalhe+'</div>'+
          '<div class="sub">'+fmtQuando(i.quando)+' · '+esc(rotulo)+'</div></div>'+
          '<span class="qtd">'+(i.pontos>=0?"+":"")+i.pontos+"</span>"+
          '</div>';
      }).join("")
    : '<p class="vazio">Sem atividades ainda.</p>';

  $("#b-mais-historico").style.display = E.historicoTemMais ? "" : "none";
}
