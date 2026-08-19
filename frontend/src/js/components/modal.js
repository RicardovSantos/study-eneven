/* Modal de confirmacao e aviso.

   Devolve o foco ao elemento que abriu o modal quando fecha, para
   quem navega por teclado nao ser jogado de volta ao topo da pagina. */

import { $ } from "../utils/dom.js";

let focoAnterior = null;

export function modal(op){
  focoAnterior = document.activeElement;
  $("#md-selo").className = "selo "+(op.selo||"ok");
  $("#md-selo").textContent = op.icone||"✓";
  $("#md-titulo").textContent = op.titulo||"";
  $("#md-texto").innerHTML = op.texto||"";
  const box=$("#md-botoes"); box.innerHTML="";
  const botoes = op.botoes||[{r:"OK",c:"btn-cinza"}];
  // dois botões ficam lado a lado, como no protótipo
  const par = botoes.length===2;
  const caixa = par ? document.createElement("div") : box;
  if(par) caixa.className="btn-par";
  botoes.forEach((b,i)=>{
    const el=document.createElement("button");
    el.type="button";
    el.className="btn "+(b.c||"btn-cinza"); el.textContent=b.r;
    if(!par && i) el.style.marginTop="8px";
    el.onclick=()=>{ fecharModal(); if(b.f) b.f(); };
    caixa.appendChild(el);
  });
  if(par) box.appendChild(caixa);
  $("#veu").classList.add("on");
  const primeiro = box.querySelector("button");
  if(primeiro) primeiro.focus();
}
export function fecharModal(){
  if(!$("#veu").classList.contains("on")) return;
  $("#veu").classList.remove("on");
  if(focoAnterior && document.contains(focoAnterior)){ try{ focoAnterior.focus(); }catch(e){} }
  focoAnterior = null;
}
