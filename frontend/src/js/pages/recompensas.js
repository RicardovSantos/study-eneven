/* Tela Prêmios: progresso nas trilhas de pontuação e os prêmios já
   desbloqueados. Só existe em modo servidor — ver router.js.

   O responsável pode trocar de beneficiário (si mesmo ou um
   dependente) num seletor; o dependente só vê os próprios dados
   (a API bloqueia o resto de qualquer forma). */

import { $ } from "../utils/dom.js";
import { E } from "../stores/app-store.js";
import { esc } from "../utils/format.js";

const ROTULO_STATUS = { unlocked: "Desbloqueado", requested: "Pedido", delivered: "Entregue" };

export function opcoesBeneficiario(){
  const eu = { id: E.usuario.id, nome: "Eu mesmo" };
  const dependentes = (E.familiaDependentes || []).map(d => ({ id: d.usuario_id, nome: d.nome }));
  return [eu, ...dependentes];
}

export function renderRecompensas(){
  const admin = E.papel === "admin";
  const opcoes = admin ? opcoesBeneficiario() : [];
  const alvoId = E.recompensasBeneficiario?.id;

  $("#rec-card-quem").style.display = (admin && opcoes.length > 1) ? "" : "none";
  if(admin && opcoes.length > 1){
    $("#rec-quem").innerHTML = opcoes.map(o => (
      '<button class="pill'+(o.id===alvoId?" on":"")+'" type="button" data-quem="'+o.id+'" data-nome="'+esc(o.nome)+'">'+esc(o.nome)+"</button>"
    )).join("");
  }
  $("#rec-nova-trilha").style.display = admin ? "" : "none";

  const trilhas = E.trilhas || [];
  if(!trilhas.length){
    $("#lista-trilhas").innerHTML = '<p class="vazio">Nenhuma trilha criada ainda.</p>';
  }else{
    $("#lista-trilhas").innerHTML = trilhas.map(t => {
      const prox = t.proximo_nivel;
      const meta = prox
        ? "Faltam "+t.faltam+" ponto(s) para: "+esc(prox.premio)
        : (t.nivel_atual ? "Todos os níveis desbloqueados!" : "Nenhum nível cadastrado ainda.");
      const pct = prox ? t.percentual : (t.nivel_atual ? 100 : 0);
      return '<div class="item" style="flex-direction:column;align-items:stretch;gap:6px">'+
        '<div class="info"><div class="nome">'+esc(t.nome)+'</div><div class="sub">'+t.pontos+' ponto(s)</div></div>'+
        '<div class="barra" style="height:14px"><i style="width:'+pct+'%"></i></div>'+
        '<div class="legenda">'+meta+"</div>"+
        (admin ? '<button class="link" type="button" data-add-nivel="'+t.trilha_id+'">+ Adicionar nível</button>' : "")+
        "</div>";
    }).join("");
  }

  const premios = E.premiosLista || [];
  if(!premios.length){
    $("#lista-premios").innerHTML = '<p class="vazio">Nenhum prêmio desbloqueado ainda.</p>';
  }else{
    $("#lista-premios").innerHTML = premios.map(p => {
      let acao = "";
      if(p.status==="unlocked" && p.beneficiario_id===E.usuario.id){
        acao = '<button class="btn btn-verde" type="button" data-solicitar="'+p.id+'">Solicitar</button>';
      }else if(p.status==="requested" && admin){
        acao = '<button class="btn btn-verde" type="button" data-entregar="'+p.id+'">Confirmar entrega</button>';
      }
      return '<div class="item">'+
        '<div class="info"><div class="nome">'+esc(p.premio)+'</div>'+
        '<div class="sub">'+esc(p.trilha_nome)+' · <span class="tag '+(p.status==="delivered"?"ok":"fixo")+'">'+
          (ROTULO_STATUS[p.status]||p.status)+"</span></div></div>"+
        acao+"</div>";
    }).join("");
  }
}
