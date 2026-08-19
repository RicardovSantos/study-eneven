/* Tela Objetivos: cadastro, edicao e exclusao (CRUD).

   E a unica tela que escreve objetivos. A tela Estudar so os executa.
   Essa separacao e a mesma que a Fase 3 vai precisar quando o
   responsavel passar a cadastrar objetivos para os dependentes. */

import { $, $$, definirSelect } from "../utils/dom.js";
import { E, salvar } from "../stores/app-store.js";
import { hoje, chaveDia, chavePeriodo } from "../utils/dates.js";
import { esc, fmtHM, id } from "../utils/format.js";
import { modal } from "../components/modal.js";
import { aviso } from "../components/toast.js";
import { alvoEfetivo, restante, tetoAcumulo } from "../services/objetivos.js";
import { ir } from "../router.js";
import { emitir, EVENTOS } from "../core/bus.js";
import { COM_SERVIDOR } from "../config.js";
import * as objetivosApi from "../api/objetivos.js";
import { ErroDaApi } from "../api/client.js";
import { paraApiObjetivo, sincronizarObjetivosCrud } from "../dados/online.js";

let editandoId = null;

export function lerPills(sel){ const b=$(sel+" .pill.on"); return b? b.dataset.v : null; }
export function marcarPill(sel,v){
  $$(sel+" .pill").forEach(b=>b.classList.toggle("on", b.dataset.v===String(v)));
}
export function textoAcumulo(){
  const ac = lerPills("#p-acum")==="1";
  const fq = lerPills("#p-freq");
  const janela = fq==="diaria" ? "até 7 dias" : fq==="semanal" ? "até 4 semanas" : "até 4 meses";
  $("#acum-txt").innerHTML = ac
    ? "<b>Acumulativo:</b> o que você não fizer soma no próximo período ("+janela+" de acúmulo). Nada se perde."
    : "<b>Não acumulativo:</b> o período vira do zero. O que não foi feito é descartado.";
}
export function atualizarFormPorTipo(){
  const est = lerPills("#p-tipo")==="estudo";
  const uniAtual = $("#f-uni").value;
  $("#f-uni").innerHTML = est
    ? '<option value="horas">horas</option><option value="minutos">minutos</option>'
    : '<option value="vezes">vezes</option>';
  if(est && (uniAtual==="horas"||uniAtual==="minutos")) $("#f-uni").value = uniAtual;
  $("#f-total").title = est ? "Total de horas até concluir" : "Total de repetições até concluir";
  $("#lb-total").textContent = est ? "Total da tarefa (horas)" : "Total da tarefa (vezes)";
}
export function limparForm(){
  editandoId=null;
  $("#form-titulo").textContent="Adicionar Objetivo";
  $("#b-salvar-item").textContent="Adicionar";
  $("#f-nome").value=""; $("#f-cat").selectedIndex=0; $("#f-status").value="andamento";
  $("#f-qtd").value=1; $("#f-total").value=360;
  marcarPill("#p-tipo","estudo"); marcarPill("#p-freq","diaria"); marcarPill("#p-acum","1");
  atualizarFormPorTipo(); textoAcumulo(); $("#erro-form").textContent="";
}
/* garante que um valor gravado apareça no <select> mesmo se não estiver na lista */
export async function salvarItem(){
  const nome=$("#f-nome").value.trim();
  const qtd=parseFloat($("#f-qtd").value);
  const total=parseFloat($("#f-total").value);
  if(!nome){ $("#erro-form").textContent="Escreva o nome do objetivo."; $("#f-nome").focus(); return; }
  if(!(qtd>0)){ $("#erro-form").textContent="A quantidade precisa ser maior que zero."; $("#f-qtd").focus(); return; }
  if(isNaN(total) || total<0){ $("#erro-form").textContent="O total da tarefa não pode ser negativo."; $("#f-total").focus(); return; }
  $("#erro-form").textContent="";
  const tipo=lerPills("#p-tipo"), uni=$("#f-uni").value;
  const alvo = tipo==="estudo" ? (uni==="horas"? qtd*60 : qtd) : qtd;
  const totalMeta = tipo==="estudo" ? (total>0? total*60 : 0) : (total>0? total : 0);
  const freq=lerPills("#p-freq");
  const acum = lerPills("#p-acum")==="1";
  const status = $("#f-status").value;

  if(COM_SERVIDOR){
    const dados = paraApiObjetivo({tipo, nome, freq, alvo, totalMeta, acum, status});
    try{
      if(editandoId) await objetivosApi.editar(editandoId, dados);
      else await objetivosApi.criar(dados);
      await sincronizarObjetivosCrud();
      const eraEdicao = !!editandoId;
      limparForm(); emitir(EVENTOS.REDESENHAR);
      modal(eraEdicao
        ? {selo:"ok",icone:"✓",titulo:"Editado",texto:"O objetivo foi atualizado.",botoes:[{r:"OK",c:"btn-verde"}]}
        : {selo:"ok",icone:"✓",titulo:"Salvo",texto:"Objetivo adicionado à sua lista.",botoes:[{r:"OK",c:"btn-verde"}]});
    }catch(e){
      $("#erro-form").textContent = e instanceof ErroDaApi ? e.message : "Não deu para salvar. Confira sua conexão.";
    }
    return;
  }

  if(editandoId){
    const it=E.itens.find(x=>x.id===editandoId);
    if(!it){ limparForm(); aviso("Esse objetivo não existe mais."); emitir(EVENTOS.REDESENHAR); return; }
    const mudouFreq = it.freq!==freq;
    Object.assign(it,{tipo,nome,cat:$("#f-cat").value,freq,qtd,uni,alvo,totalMeta,
      acum:lerPills("#p-acum")==="1", status:$("#f-status").value});
    if(mudouFreq){ it.saldo=0; it.feito=0; it.periodoRef=chavePeriodo(freq,hoje()); }
    it.saldo = Math.min(it.saldo||0, tetoAcumulo(it));
    it.feito = Math.min(it.feito||0, alvoEfetivo(it));
    salvar(true); limparForm(); emitir(EVENTOS.REDESENHAR);
    modal({selo:"ok",icone:"✓",titulo:"Editado",texto:"O objetivo foi atualizado.",botoes:[{r:"OK",c:"btn-verde"}]});
    return;
  }
  E.itens.push({
    id:id(), tipo, nome, cat:$("#f-cat").value, freq, qtd, uni, alvo, totalMeta,
    acum:lerPills("#p-acum")==="1", status:$("#f-status").value,
    feito:0, saldo:0, progresso:0, periodoRef:chavePeriodo(freq,hoje()),
    criadoEm:chaveDia(), ultimaConclusao:null
  });
  salvar(true); limparForm(); emitir(EVENTOS.REDESENHAR);
  modal({selo:"ok",icone:"✓",titulo:"Salvo",texto:"Objetivo adicionado à sua lista.",botoes:[{r:"OK",c:"btn-verde"}]});
}
export function editarItem(idv){
  const it=E.itens.find(x=>x.id===idv); if(!it) return;
  editandoId=idv;
  $("#form-titulo").textContent="Editar Objetivo";
  $("#b-salvar-item").textContent="Editar";
  marcarPill("#p-tipo",it.tipo); atualizarFormPorTipo();
  $("#f-nome").value=it.nome;
  definirSelect("#f-cat", it.cat);
  $("#f-status").value=it.status;
  marcarPill("#p-freq",it.freq); marcarPill("#p-acum", it.acum?"1":"0");
  $("#f-qtd").value=it.qtd; definirSelect("#f-uni", it.uni);
  $("#f-total").value = it.tipo==="estudo" ? Math.round((it.totalMeta||0)/60) : (it.totalMeta||0);
  textoAcumulo();
  ir("objetivos");
  $("#tela-objetivos .card").scrollIntoView({block:"start",behavior:"smooth"});
  $("#f-nome").focus();
}
export function excluirItem(idv){
  const it=E.itens.find(x=>x.id===idv); if(!it) return;
  modal({selo:"perigo",icone:"🗑",titulo:"Excluir Objetivo",
    texto:"<b>Nome:</b> "+esc(it.nome)+"<br><b>Andamento:</b> "+(it.status==="concluido"?"Concluído":"Andamento")+
      "<br><span style='color:#E23B3B'>Confirme os dados antes de excluir.</span>",
    botoes:[
      {r:"Excluir",c:"btn-vermelho",f: async ()=>{
        if(COM_SERVIDOR){
          try{
            const r = await objetivosApi.excluir(idv);
            await sincronizarObjetivosCrud();
            if(editandoId===idv) limparForm();
            emitir(EVENTOS.REDESENHAR);
            modal({selo:"perigo",icone: r.excluido?"🗑":"📦",
              titulo: r.excluido?"Excluído":"Arquivado", texto:r.detalhe,
              botoes:[{r:"OK",c:"btn-cinza"}]});
          }catch(e){
            aviso(e instanceof ErroDaApi ? e.message : "Não deu para excluir. Confira sua conexão.");
          }
          return;
        }
        E.itens = E.itens.filter(x=>x.id!==idv);
        if(editandoId===idv) limparForm();
        salvar(true); emitir(EVENTOS.REDESENHAR);
        modal({selo:"perigo",icone:"🗑",titulo:"Excluído",texto:"O objetivo saiu da sua lista.",botoes:[{r:"OK",c:"btn-cinza"}]});
      }},
      {r:"Cancelar",c:"btn-azul"}
    ]});
}
export function renderCrud(){
  const busca=$("#f-busca").value.trim().toLowerCase();
  const lista=E.itens.filter(it=> !busca
    || String(it.nome||"").toLowerCase().includes(busca)
    || String(it.cat||"").toLowerCase().includes(busca));
  if(!lista.length){
    $("#lista-crud").innerHTML = '<p class="vazio">'+(E.itens.length
      ? "Nada encontrado para essa busca."
      : "Você ainda não cadastrou objetivos.<br>Preencha o formulário acima para começar.")+"</p>";
    return;
  }
  $("#lista-crud").innerHTML = lista.map(it=>{
    const un = it.tipo==="estudo" ? fmtHM(it.alvo) : it.qtd+"x";
    const fr = {diaria:"por dia",semanal:"por semana",mensal:"por mês"}[it.freq]||"";
    return '<div class="item">'+
      '<div class="info"><div class="nome">'+esc(it.nome)+'</div>'+
      '<div class="sub"><span class="tag cat">'+esc(it.cat)+'</span>'+
      '<span class="tag '+(it.acum?"acum":"fixo")+'">'+(it.acum?"acumulativo":"fixo")+'</span>'+
      (it.status==="concluido"?'<span class="tag ok">concluído</span>':"")+
      '</div></div>'+
      '<span class="qtd">'+un+"<br><small>"+fr+"</small></span>"+
      '<button class="icone-btn del" type="button" data-del="'+it.id+'" aria-label="Excluir '+esc(it.nome)+'">🗑</button>'+
      '<button class="icone-btn edit" type="button" data-edit="'+it.id+'" aria-label="Editar '+esc(it.nome)+'">✎</button>'+
      '</div>';
  }).join("");
}
