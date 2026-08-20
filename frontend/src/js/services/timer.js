/* Cronometro da sessao de foco.

   MODO LOCAL: o tempo e calculado por diferenca de Date.now() a cada
   tique, e nao somando 1 a cada intervalo — se a aba dorme ou o
   navegador atrasa o timer, a contagem continua correta ao voltar. O
   tempo e gravado no objetivo a cada 30 segundos (`descarregar`), para
   uma queda de energia nao levar a sessao junto.

   MODO API: a contagem visual continua sendo local (mesma resposta
   imediata de sempre), mas quem manda no tempo que vira ponto e o
   servidor — ver docs/api.md, secao "Sessões de estudo". A cada 30
   segundos o cliente manda um heartbeat; `tocar` abre uma sessao de
   verdade, `pausar`/`encerrar` chamam a API. Se o heartbeat falhar (sem
   rede), so avisa e tenta de novo no proximo ciclo — o relogio local
   continua andando normalmente.

   Nao importa o relogio flutuante: avisa por SESSAO_MUDOU. */

import { $ } from "../utils/dom.js";
import { E, salvar } from "../stores/app-store.js";
import { esc, fmtHM, fmtRelogio } from "../utils/format.js";
import { modal } from "../components/modal.js";
import { aviso } from "../components/toast.js";
import { alvoEfetivo, restante, creditarEstudo, concluirCiclo } from "./objetivos.js";
import { emitir, em, EVENTOS } from "../core/bus.js";
import { COM_SERVIDOR } from "../config.js";
import * as sessoesApi from "../api/sessoes.js";
import { ErroDaApi } from "../api/client.js";
import { sincronizarOcorrenciasEstudar } from "../dados/online.js";
import { ofereceAdiantar } from "./adiantamento.js";

export const T = {itemId:null, sessaoId:null, restanteSeg:0, totalSeg:0, rodando:false, ultimo:0, acumulado:0};
let loop=null;

export function abrirFoco(idv){
  const it=E.itens.find(x=>x.id===idv); if(!it) return;
  if(T.rodando && T.itemId && T.itemId!==idv){
    const anterior = E.itens.find(x=>x.id===T.itemId);
    modal({selo:"info",icone:"⏱",titulo:"Cronômetro em uso",
      texto:"<b>"+esc(anterior? anterior.nome : "Outro objetivo")+"</b> está rodando agora."+
        "<br>Quer pausar e trocar para <b>"+esc(it.nome)+"</b>?",
      botoes:[{r:"Trocar",c:"btn-roxo",f: async ()=>{ await pausar(true); montarFoco(it); }},{r:"Cancelar",c:"btn-cinza"}]});
    return;
  }
  if(T.rodando && T.itemId===idv){ $("#foco").classList.add("on"); emitir(EVENTOS.SESSAO_MUDOU); return; }
  montarFoco(it);
}
export function montarFoco(it){
  T.itemId=it.id; T.sessaoId=null; T.rodando=false; T.acumulado=0;
  T.totalSeg = alvoEfetivo(it)*60;
  T.restanteSeg = restante(it)*60;
  $("#fc-cat").textContent = it.cat+" · "+({diaria:"diário",semanal:"semanal",mensal:"mensal"}[it.freq]||"");
  $("#fc-titulo").textContent = it.nome;
  $("#fc-meta").textContent = "Meta do período: "+fmtHM(alvoEfetivo(it))+
    ((it.saldo||0)>0 ? " (inclui "+fmtHM(it.saldo)+" acumulados)" : "");
  pintarFoco();
  $("#foco").classList.add("on");
  $("#fc-toggle").focus();
  emitir(EVENTOS.SESSAO_MUDOU);
}
export function pintarFoco(){
  $("#fc-tempo").textContent = fmtRelogio(T.restanteSeg);
  const r=94, c=2*Math.PI*r;
  const frac = T.totalSeg ? (T.restanteSeg/T.totalSeg) : 0;
  const arco=$("#fc-arco");
  arco.setAttribute("stroke-dasharray", c.toFixed(1));
  arco.setAttribute("stroke-dashoffset", (c*(1-frac)).toFixed(1));
  atualizarPonta(frac);
  $("#fc-anel").classList.toggle("rodando", T.rodando);
  pintarControles();
}
/* Ponta do relógio: um pontinho no fim do arco visível, pra reforçar que
   o tempo está mesmo correndo (mesma matemática do arco, só que
   convertida pra um ponto — ver comentário da seção 7 sobre o SVG
   estar rotacionado -90° via CSS: o cálculo abaixo usa o ângulo "antes"
   dessa rotação, e o navegador rotaciona o ponto junto com o arco). */
export function atualizarPonta(frac){
  const p=$("#fc-ponta"); if(!p) return;
  const t = frac*2*Math.PI, r=94;
  p.setAttribute("cx", (105 + r*Math.cos(t)).toFixed(2));
  p.setAttribute("cy", (105 + r*Math.sin(t)).toFixed(2));
}
/* Botão único de play/pausa + botão de sair com ícone/legenda que mudam
   conforme o estado: rodando -> "minimizar" (some da tela, mas o tempo
   continua contando na tarja flutuante); pausado -> "encerrar" (para de
   vez e sai, sem impressão de que ia só "fechar"). */
export function pintarControles(){
  $(".ic-play").style.display = T.rodando ? "none" : "flex";
  $(".ic-pause").style.display = T.rodando ? "flex" : "none";
  $("#fc-toggle").setAttribute("aria-label", T.rodando ? "Pausar" : "Iniciar cronômetro");
  $("#fc-legenda-toggle").textContent = T.rodando ? "Pausar" : "Iniciar";
  $(".ic-minimizar").style.display = T.rodando ? "flex" : "none";
  $(".ic-encerrar").style.display = T.rodando ? "none" : "flex";
  $("#fc-fechar").setAttribute("aria-label", T.rodando ? "Minimizar" : "Encerrar e sair");
  $("#fc-legenda-sair").textContent = T.rodando ? "Minimizar" : "Encerrar";
  $("#fc-dica").textContent = T.rodando
    ? "Minimizar mantém o tempo contando na tarja flutuante."
    : "Encerrar salva o tempo já feito e sai do cronômetro.";
}
export async function tocar(){
  if(T.rodando || !T.itemId) return;
  if(T.restanteSeg<=0){ aviso("Este objetivo já está concluído no período."); return; }

  if(COM_SERVIDOR){
    const it = E.itens.find(x=>x.id===T.itemId);
    try{
      if(!T.sessaoId){
        const s = await sessoesApi.abrir({
          objetivo_id: it?.objetivoId, ocorrencia_id: it?.ocorrenciaId || T.itemId,
        });
        T.sessaoId = s.id;
      }else{
        await sessoesApi.retomar(T.sessaoId);
      }
    }catch(e){
      aviso(e instanceof ErroDaApi ? e.message : "Não deu para iniciar a sessão. Confira sua conexão.");
      return;
    }
  }

  T.rodando=true; T.ultimo=Date.now();
  if(loop) clearInterval(loop);
  loop=setInterval(tique,250);
  pintarFoco();
  emitir(EVENTOS.SESSAO_MUDOU);
}
export function tique(){
  if(!T.rodando) return;
  const agora=Date.now(), delta=(agora-T.ultimo)/1000;
  T.ultimo=agora;
  if(delta<=0) return;
  T.restanteSeg = Math.max(0, T.restanteSeg-delta);
  T.acumulado += delta;
  $("#fc-tempo").textContent = fmtRelogio(T.restanteSeg);
  const r=94,c=2*Math.PI*r, frac = T.totalSeg? T.restanteSeg/T.totalSeg : 0;
  $("#fc-arco").setAttribute("stroke-dashoffset", (c*(1-frac)).toFixed(1));
  atualizarPonta(frac);
  const seg = Math.round(T.restanteSeg);
  if(seg !== ultimoSegVisto){ ultimoSegVisto = seg; emitir(EVENTOS.SESSAO_MUDOU); }
  if(T.acumulado>=30){ descarregar(); if(!COM_SERVIDOR) salvar(); }
  if(T.restanteSeg<=0) zerou();
}
let ultimoSegVisto = -1;
/* Fire-and-forget de propósito: nem tique() nem os pontos de chamada
   abaixo esperam esta função terminar — o relógio na tela não pode
   travar esperando a rede. Uma falha de heartbeat só é avisada; o
   tempo local continua contando e o próximo ciclo tenta de novo. */
export async function descarregar(){
  if(T.acumulado<=0) return;
  const acumulado = T.acumulado;
  T.acumulado = 0;

  if(COM_SERVIDOR){
    if(!T.sessaoId) return;
    try{ await sessoesApi.heartbeat(T.sessaoId); }
    catch(e){ console.warn("heartbeat falhou:", e.message); }
    return;
  }

  const it=E.itens.find(x=>x.id===T.itemId);
  if(it) creditarEstudo(it, acumulado/60);
}
export async function pausar(silencioso){
  if(!T.rodando) return;
  T.rodando=false; clearInterval(loop); loop=null;
  await descarregar();
  if(COM_SERVIDOR){
    if(T.sessaoId){ try{ await sessoesApi.pausar(T.sessaoId); }catch(e){ /* segue mesmo assim */ } }
  }else{
    salvar(true);
  }
  pintarFoco(); emitir(EVENTOS.REDESENHAR); emitir(EVENTOS.SESSAO_MUDOU);
  if(!silencioso) aviso("Pausado. O tempo já feito foi salvo.");
}
export async function encerrar(){
  const it=E.itens.find(x=>x.id===T.itemId);
  T.rodando=false; clearInterval(loop); loop=null;
  await descarregar();

  let avisoTexto = it ? "Sessão encerrada. "+fmtHM(restante(it))+" ainda faltam." : "Sessão encerrada.";
  if(COM_SERVIDOR && T.sessaoId){
    try{
      const r = await sessoesApi.finalizar(T.sessaoId, {});
      avisoTexto = r.pontos_creditados>0
        ? "Sessão encerrada. +"+r.pontos_creditados+" pontos."
        : "Sessão encerrada.";
      await sincronizarOcorrenciasEstudar();
      if(r.ocorrencia_concluida) await ofereceAdiantar(r.sessao.ocorrencia_id, it?.nome);
    }catch(e){
      aviso(e instanceof ErroDaApi ? e.message : "Não deu para encerrar no servidor.");
    }
  }else if(!COM_SERVIDOR){
    salvar(true);
  }

  T.sessaoId=null;
  $("#foco").classList.remove("on");
  T.itemId=null;
  emitir(EVENTOS.FECHAR_PIP);
  emitir(EVENTOS.REDESENHAR); emitir(EVENTOS.SESSAO_MUDOU);
  aviso(avisoTexto);
}
export function fecharFoco(){
  // minimizar não pausa mais: o relógio continua correndo na tarja flutuante
  $("#foco").classList.remove("on");
  emitir(EVENTOS.REDESENHAR);
  emitir(EVENTOS.SESSAO_MUDOU);
  if(T.rodando) aviso("Continua contando aqui embaixo.");
}
export async function zerou(){
  T.rodando=false; clearInterval(loop); loop=null;
  await descarregar();
  const it=E.itens.find(x=>x.id===T.itemId);

  if(COM_SERVIDOR && T.sessaoId){
    try{
      const r = await sessoesApi.finalizar(T.sessaoId, {});
      await sincronizarOcorrenciasEstudar();
      if(r.ocorrencia_concluida){
        aviso("Concluído! +"+r.pontos_creditados+" pontos.");
        await ofereceAdiantar(r.sessao.ocorrencia_id, it?.nome);
      }
    }catch(e){
      aviso(e instanceof ErroDaApi ? e.message : "Não deu para encerrar no servidor.");
    }
    T.sessaoId=null;
  }

  T.itemId=null;
  emitir(EVENTOS.FECHAR_PIP);
  $("#foco").classList.remove("on");
  emitir(EVENTOS.SESSAO_MUDOU);
  if(!COM_SERVIDOR && it) concluirCiclo(it,true);
}

/* O relogio flutuante pede a reabertura do foco por evento, para nao
   precisar importar este modulo de volta. */
em(EVENTOS.ABRIR_FOCO, idv => abrirFoco(idv));
