/* Relogio flutuante — tres camadas, da mais compativel para a menos:

   1. tarja dentro do app — funciona em todo navegador;
   2. Document Picture-in-Picture — janela real do sistema, sempre por
      cima, mesmo com o navegador minimizado (Chrome/Edge no desktop);
   3. Picture-in-Picture de video via canvas — usado onde a de cima nao
      existe; no Chrome do Android ele flutua sobre os outros apps.

   Nenhuma web app consegue desenhar por cima do sistema sem uma dessas
   APIs, entao quando nenhuma existe fica so a camada 1. E a limitacao
   que a Fase 9 resolve no Android, com overlay nativo.

   Le o estado do cronometro (T), mas nunca o chama de volta: para
   reabrir o foco emite ABRIR_FOCO. */

import { $ } from "../utils/dom.js";
import { E } from "../stores/app-store.js";
import { fmtRelogio } from "../utils/format.js";
import { aviso } from "./toast.js";
import { T } from "../services/timer.js";
import { emitir, em, EVENTOS } from "../core/bus.js";

export const podeDocPiP = ("documentPictureInPicture" in window);
export const podeVideoPiP = !!(document.pictureInPictureEnabled &&
  document.createElement("video").requestPictureInPicture &&
  window.HTMLCanvasElement && HTMLCanvasElement.prototype.captureStream);
let jPiP=null, cvPiP=null, vidPiP=null, loopPiP=null;

/* Posição arrastada da tarja: null enquanto o usuário não move — nesse
   caso ela usa o canto padrão (right/bottom do CSS). Depois de um
   arraste, guarda em pixels (relativos a #app) onde ela foi deixada,
   e todo redesenho — trocar de aba, retomar o cronômetro — passa a
   respeitar essa posição em vez de voltar ao canto. */
let miniPos = null;
export function aplicarPosicaoMini(){
  if(!miniPos) return;
  const mini = $("#mini");
  mini.style.left = miniPos.left+"px";
  mini.style.top = miniPos.top+"px";
  mini.style.right = "auto";
  mini.style.bottom = "auto";
}
export function reencaixarMini(){
  if(!miniPos) return;
  const mini=$("#mini"), app=$("#app").getBoundingClientRect(), r=mini.getBoundingClientRect();
  const margem=6;
  miniPos.left = Math.max(margem, Math.min(app.width  - r.width  - margem, miniPos.left));
  miniPos.top  = Math.max(margem, Math.min(app.height - r.height - margem, miniPos.top));
  aplicarPosicaoMini();
}

export function sincronizarFlutuante(){
  const it = T.itemId ? E.itens.find(x=>x.id===T.itemId) : null;
  const focoAberto = $("#foco").classList.contains("on");
  const mini = $("#mini");
  mini.classList.toggle("on", !!it && !focoAberto && E.logado);
  mini.classList.toggle("rodando", T.rodando);
  mini.classList.toggle("parado", !T.rodando);
  if(it){
    $("#mini-tempo").textContent = fmtRelogio(T.restanteSeg);
    $("#mini-nome").textContent = it.nome;
  }
  aplicarPosicaoMini();
  pintarPiP(it);
}
export function pintarPiP(it){
  if(jPiP && !jPiP.closed){
    const d=jPiP.document;
    const t=d.getElementById("t"), n=d.getElementById("n"), p=d.getElementById("p");
    if(t) t.textContent = fmtRelogio(T.restanteSeg);
    if(n) n.textContent = it ? it.nome : "";
    if(p) p.style.background = T.rodando ? "#56D364" : "#F2B705";
  }
  if(cvPiP) desenharPiP(it);
}
export function desenharPiP(it){
  if(!cvPiP) return;
  const c=cvPiP.getContext("2d"), L=cvPiP.width, A=cvPiP.height;
  const fonte='system-ui,-apple-system,"Segoe UI",Roboto,sans-serif';
  c.fillStyle="#2B2A63"; c.fillRect(0,0,L,A);
  c.textAlign="center";
  c.fillStyle="#fff"; c.font="700 76px "+fonte;
  c.fillText(fmtRelogio(T.restanteSeg), L/2, A/2+16);
  c.fillStyle="#C9C6F2"; c.font="600 26px "+fonte;
  c.fillText(((it&&it.nome)||"").slice(0,26).toUpperCase(), L/2, A/2+62);
  c.beginPath(); c.arc(L/2, A/2-64, 12, 0, Math.PI*2);
  c.fillStyle = T.rodando ? "#56D364" : "#F2B705"; c.fill();
}
export function limparVideoPiP(){
  if(loopPiP){ clearInterval(loopPiP); loopPiP=null; }
  if(vidPiP){ try{ vidPiP.pause(); }catch(e){} vidPiP.remove(); vidPiP=null; }
  cvPiP=null;
}
export function fecharPiP(){
  if(jPiP && !jPiP.closed){ try{ jPiP.close(); }catch(e){} }
  jPiP=null;
  if(document.pictureInPictureElement){ document.exitPictureInPicture().catch(()=>{}); }
  limparVideoPiP();
}
export async function soltarPiP(){
  // segundo toque fecha a janela
  if((jPiP && !jPiP.closed) || document.pictureInPictureElement){ fecharPiP(); return; }
  const it = T.itemId ? E.itens.find(x=>x.id===T.itemId) : null;
  if(!it){ aviso("Nenhum cronômetro aberto."); return; }
  try{
    if(podeDocPiP){
      jPiP = await window.documentPictureInPicture.requestWindow({width:300,height:170});
      const d=jPiP.document;
      d.documentElement.lang="pt-BR";
      const st=d.createElement("style");
      st.textContent='html,body{margin:0;height:100%}'+
        'body{background:#2B2A63;color:#fff;display:flex;flex-direction:column;align-items:center;'+
        'justify-content:center;gap:8px;cursor:pointer;'+
        'font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}'+
        '#p{width:11px;height:11px;border-radius:50%;background:#56D364}'+
        '#t{font-size:42px;font-weight:800;font-variant-numeric:tabular-nums;letter-spacing:.02em}'+
        '#n{font-size:11px;font-weight:600;color:#C9C6F2;text-transform:uppercase;letter-spacing:.06em;'+
        'max-width:90%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}';
      d.head.appendChild(st);
      d.body.innerHTML='<div id="p"></div><div id="t">00:00:00</div><div id="n"></div>';
      d.body.addEventListener("click", ()=>{ window.focus(); emitir(EVENTOS.ABRIR_FOCO, T.itemId); });
      jPiP.addEventListener("pagehide", ()=>{ jPiP=null; sincronizarFlutuante(); });
      pintarPiP(it);
      aviso("Relógio solto em janela flutuante.");
      return;
    }
    if(podeVideoPiP){
      cvPiP=document.createElement("canvas"); cvPiP.width=480; cvPiP.height=270;
      desenharPiP(it);
      vidPiP=document.createElement("video");
      vidPiP.srcObject=cvPiP.captureStream(2);
      vidPiP.muted=true; vidPiP.playsInline=true; vidPiP.setAttribute("playsinline","");
      vidPiP.style.cssText="position:fixed;left:-9999px;top:0;width:2px;height:2px;opacity:0";
      document.body.appendChild(vidPiP);
      loopPiP=setInterval(()=>desenharPiP(T.itemId?E.itens.find(x=>x.id===T.itemId):null),500);
      await vidPiP.play();
      await vidPiP.requestPictureInPicture();
      vidPiP.addEventListener("leavepictureinpicture", limparVideoPiP, {once:true});
      aviso("Relógio solto em janela flutuante.");
      return;
    }
    aviso("Este navegador não permite soltar a janela.");
  }catch(e){
    fecharPiP();
    aviso("O navegador recusou abrir a janela flutuante.");
  }
}

/* Arrastar a tarja: aperta, segura e solta em qualquer canto da tela.
   Pointer Events cobre mouse e toque com a mesma lógica.

   Detalhe que não é óbvio: setPointerCapture redireciona TODOS os
   eventos do ponteiro capturado para o elemento que capturou — inclusive
   o "click" sintético que o navegador dispara ao soltar. Isso quer dizer
   que, com a captura ativa, um toque parado nos botões internos
   (#mini-abrir, #mini-pip, #mini-fechar) nunca dispararia o onclick
   deles, porque o clique chegaria em #mini, não neles. Por isso o toque
   sem arrasto é tratado manualmente aqui: guardamos qual botão recebeu o
   pointerdown e, se não houve movimento, chamamos .click() nele por
   código — e sempre suprimimos o clique fantasma que o navegador ia
   mandar para #mini, pra não disparar nada em dobro. */
export function ativarArrasto(){
  const mini = $("#mini");
  const LIMIAR = 6;
  let ativo=false, moveu=false, pid=null, alvoInicial=null;
  let offX=0, offY=0, appRect=null, miniW=0, miniH=0, iniX=0, iniY=0;

  function suprimirProximoClique(){
    const bloquear = ev=>{ ev.stopPropagation(); ev.preventDefault(); };
    mini.addEventListener("click", bloquear, {capture:true, once:true});
  }
  function posicionar(clientX, clientY){
    const margem = 6;
    let left = clientX - appRect.left - offX;
    let top  = clientY - appRect.top  - offY;
    left = Math.max(margem, Math.min(appRect.width  - miniW - margem, left));
    top  = Math.max(margem, Math.min(appRect.height - miniH - margem, top));
    miniPos = {left, top};
    aplicarPosicaoMini();
  }
  mini.addEventListener("pointerdown", e=>{
    if(e.button!=null && e.button!==0) return; // só o botão principal do mouse
    ativo=true; moveu=false; pid=e.pointerId;
    iniX=e.clientX; iniY=e.clientY;
    alvoInicial = e.target.closest("#mini-abrir,#mini-pip,#mini-fechar");
    const r=mini.getBoundingClientRect();
    appRect=$("#app").getBoundingClientRect();
    offX=e.clientX-r.left; offY=e.clientY-r.top;
    miniW=r.width; miniH=r.height;
    try{ mini.setPointerCapture(pid); }catch(err){}
  });
  mini.addEventListener("pointermove", e=>{
    if(!ativo) return;
    if(!moveu && Math.hypot(e.clientX-iniX, e.clientY-iniY) > LIMIAR){
      moveu=true; mini.classList.add("arrastando");
    }
    if(moveu) posicionar(e.clientX, e.clientY);
  });
  function soltar(e){
    if(!ativo) return;
    ativo=false;
    mini.classList.remove("arrastando");
    try{ mini.releasePointerCapture(pid); }catch(err){}
    // ordem importa: o clique de baixo primeiro (senão o bloqueio abaixo,
    // por estar no caminho de captura até o botão-alvo, o engoliria também)
    if(!moveu && alvoInicial) alvoInicial.click();   // toque real: aciona o botão tocado por código
    suprimirProximoClique();       // o clique-fantasma nativo, se vier, chegaria em #mini — descarta
  }
  mini.addEventListener("pointerup", soltar);
  mini.addEventListener("pointercancel", soltar);
}

/* O cronometro avisa por evento quando a sessao muda de estado. */
em(EVENTOS.SESSAO_MUDOU, () => sincronizarFlutuante());
em(EVENTOS.FECHAR_PIP,   () => fecharPiP());
em(EVENTOS.IR_PARA,      () => sincronizarFlutuante());
