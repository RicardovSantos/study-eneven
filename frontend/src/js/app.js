/* Ponto de entrada.

   Faz tres coisas, nesta ordem: importa os modulos (o que registra os
   ouvintes do barramento), liga os eventos do DOM e carrega o estado
   guardado antes de mostrar a primeira tela.

   Os `import` de CSS sao resolvidos pelo Vite no build; em
   desenvolvimento ele os injeta na pagina. */

import "../css/tokens.css";
import "../css/reset.css";
import "../css/layout.css";
import "../css/components.css";
import "../css/pages.css";
import "../css/responsive.css";

import { $, $$ } from "./utils/dom.js";
import { Store } from "./stores/storage.js";
import { E, CHAVE, salvar, carregar, apagarTudo, estadoNovo } from "./stores/app-store.js";
import { hoje, chaveDia, chavePeriodo } from "./utils/dates.js";
import { modal, fecharModal } from "./components/modal.js";
import { aviso } from "./components/toast.js";
import { bip } from "./utils/sound.js";
import { ir } from "./router.js";
import {
  alvoEfetivo, restante, pontosDe, virarPeriodos,
  registrarHistorico, concluirCiclo, desfazerCiclo
} from "./services/objetivos.js";
import {
  T, abrirFoco, tocar, pausar, encerrar, fecharFoco, descarregar, tique
} from "./services/timer.js";
import {
  sincronizarFlutuante, reencaixarMini, fecharPiP, soltarPiP,
  ativarArrasto, podeDocPiP, podeVideoPiP
} from "./components/floating-clock.js";
import { renderTudo } from "./pages/index.js";
import { renderCrud, salvarItem, editarItem, excluirItem, limparForm,
         atualizarFormPorTipo, textoAcumulo } from "./pages/objetivos.js";
import { entrar, criarConta, recuperar } from "./auth/local-auth.js";
import { lerFoto } from "./utils/image.js";
import { carregarDemo } from "./utils/demo.js";
import { exportarBackup } from "./utils/backup.js";

/* ---------- Eventos ---------- */
$$(".nav-btn").forEach(b=>b.onclick=()=>ir(b.dataset.ir));
$("#b-entrar").onclick=entrar;
$("#in-email").addEventListener("keydown",e=>{ if(e.key==="Enter") $("#in-senha").focus(); });
$("#in-senha").addEventListener("keydown",e=>{ if(e.key==="Enter") entrar(); });
$("#b-ir-cadastro").onclick=()=>ir("cadastro");
$("#b-esqueci").onclick=()=>ir("esqueci");
$("#b-criar").onclick=criarConta;
$("#cad-senha2").addEventListener("keydown",e=>{ if(e.key==="Enter") criarConta(); });
$("#b-recuperar").onclick=recuperar;
$("#rec-nova").addEventListener("keydown",e=>{ if(e.key==="Enter") recuperar(); });
$("#b-ajuda").onclick=()=>modal({selo:"info",icone:"?",titulo:"Ajuda do suporte",
  texto:"O DevLog roda inteiro no seu aparelho, sem servidor e sem cadastro remoto.<br><br>"+
    "Se você esqueceu o email da conta, use <b>Apagar tudo</b> na aba Perfil e comece de novo — "+
    "exporte os dados antes, se quiser guardar o histórico.",
  botoes:[{r:"Entendi",c:"btn-azul"}]});
$$("[data-voltar-login]").forEach(b=>b.onclick=()=>ir("login"));

["#p-tipo","#p-freq","#p-acum"].forEach(sel=>{
  $(sel).addEventListener("click",e=>{
    const b=e.target.closest(".pill"); if(!b) return;
    $$(sel+" .pill").forEach(x=>x.classList.remove("on"));
    b.classList.add("on");
    if(sel==="#p-tipo") atualizarFormPorTipo();
    textoAcumulo();
  });
});
$("#b-salvar-item").onclick=salvarItem;
$("#f-nome").addEventListener("keydown",e=>{ if(e.key==="Enter") salvarItem(); });
$("#b-cancelar-item").onclick=()=>{ limparForm(); aviso("Formulário limpo."); };
$("#f-busca").addEventListener("input",renderCrud);
$("#f-busca").addEventListener("keydown",e=>{ if(e.key==="Enter"){ e.preventDefault(); renderCrud(); } });
$("#b-pesquisar").onclick=()=>{ renderCrud(); $("#lista-crud").scrollIntoView({block:"nearest",behavior:"smooth"}); };
$("#lista-crud").addEventListener("click",e=>{
  const d=e.target.closest("[data-del]"), ed=e.target.closest("[data-edit]");
  if(d) excluirItem(d.dataset.del);
  else if(ed) editarItem(ed.dataset.edit);
});

$("#tela-estudar").addEventListener("click",e=>{
  const pl=e.target.closest("[data-play]");
  const ck=e.target.closest("[data-check]");
  const ma=e.target.closest("[data-mais]");
  const rb=e.target.closest("[data-reabrir]");
  if(pl){ abrirFoco(pl.dataset.play); return; }
  if(ma){
    const it=E.itens.find(x=>x.id===ma.dataset.mais); if(!it) return;
    if(restante(it)<=0){ aviso("Já concluído neste período."); return; }
    // pontos e alvo são lidos antes de mexer no saldo, senão mudam no meio do caminho
    const pts = pontosDe(it), alvoCiclo = alvoEfetivo(it), saldoAntes = it.saldo||0, statusAntes = it.status;
    it.feito=(it.feito||0)+1; it.progresso=(it.progresso||0)+1;
    if(restante(it)<=0){
      E.pontos+=pts; E.concluidos+=1; registrarHistorico(0,1,pts);
      it.saldo=0; it.ultimaConclusao=chaveDia();
      it.desfazer={feito:0, saldo:saldoAntes, status:statusAntes, credito:alvoCiclo, pontos:pts};
      if(it.totalMeta>0 && it.progresso>=it.totalMeta) it.status="concluido";
      bip(920,.3); aviso("Concluído! +"+pts+" pontos");
    }
    salvar(true); renderTudo();
    return;
  }
  if(ck){
    const it=E.itens.find(x=>x.id===ck.dataset.check); if(!it) return;
    if(restante(it)<=0) desfazerCiclo(it); else concluirCiclo(it,true);
    return;
  }
  if(rb){
    const it=E.itens.find(x=>x.id===rb.dataset.reabrir); if(!it) return;
    it.status="andamento"; it.feito=0; it.periodoRef=chavePeriodo(it.freq,hoje());
    salvar(true); renderTudo(); aviso("Objetivo reaberto.");
  }
});

$("#fc-toggle").onclick=()=> T.rodando ? pausar(false) : tocar();
// sair muda de comportamento conforme o estado (ver pintarControles): rodando
// minimiza (tempo continua na tarja flutuante), pausado encerra de vez.
$("#fc-fechar").onclick=()=> T.rodando ? fecharFoco() : encerrar();

/* Relógio flutuante */
$("#mini-abrir").onclick=()=>{ if(T.itemId) abrirFoco(T.itemId); };
$("#mini-pip").onclick=soltarPiP;
$("#mini-fechar").onclick=()=>{
  modal({selo:"info",icone:"⏱",titulo:"Encerrar sessão",
    texto:"O tempo já cronometrado fica salvo.",
    botoes:[{r:"Encerrar",c:"btn-vermelho",f:encerrar},{r:"Continuar",c:"btn-cinza"}]});
};
// o botão de soltar só aparece onde o navegador tem alguma API de janela flutuante
$("#mini-pip").classList.toggle("on", podeDocPiP || podeVideoPiP);
$("#mini-fechar").classList.add("on");
// mantém a tarja dentro da tela se a janela mudar de tamanho (giro do aparelho, teclado etc.)
window.addEventListener("resize", reencaixarMini);

$("#b-foto").onclick=()=>$("#in-foto").click();
$("#in-foto").addEventListener("change",e=>{ if(e.target.files[0]) lerFoto(e.target.files[0]); e.target.value=""; });
$("#b-tirar-foto").onclick=()=>{ if(E.usuario){ E.usuario.foto=null; salvar(true); renderTudo(); aviso("Foto removida."); } };
$("#b-salvar-perfil").onclick=()=>{
  if(!E.usuario){ $("#erro-perfil").textContent="Nenhuma conta ativa neste aparelho."; return; }
  const nome=$("#pf-nome").value.trim(), em=$("#pf-email").value.trim(), se=$("#pf-senha").value;
  if(nome.length<2){ $("#erro-perfil").textContent="Escreva seu nome."; return; }
  if(!/^\S+@\S+\.\S+$/.test(em)){ $("#erro-perfil").textContent="Email inválido."; return; }
  if(se && se.length<4){ $("#erro-perfil").textContent="A senha precisa de ao menos 4 caracteres."; return; }
  if(!$("#pf-termos").checked){ $("#erro-perfil").textContent="É preciso aceitar os termos."; return; }
  $("#erro-perfil").textContent="";
  Object.assign(E.usuario,{nome,email:em,nasc:$("#pf-nasc").value,sexo:$("#pf-sexo").value,
    escola:$("#pf-escola").value,pais:$("#pf-pais").value,termos:true});
  if(se) E.usuario.senha=se;              // em branco = mantém a senha atual
  salvar(true); renderTudo();
  modal({selo:"ok",icone:"✓",titulo:"Salvo",texto:"Seu perfil foi atualizado.",botoes:[{r:"OK",c:"btn-verde"}]});
};
$("#b-demo").onclick=()=>modal({selo:"info",icone:"⚙",titulo:"Carregar exemplo",
  texto:"Isso substitui seus objetivos e o histórico por dados de demonstração.",
  botoes:[{r:"Carregar",c:"btn-roxo",f:carregarDemo},{r:"Cancelar",c:"btn-cinza"}]});
$("#b-exportar").onclick=exportarBackup;
$("#b-zerar").onclick=()=>modal({selo:"perigo",icone:"🗑",titulo:"Apagar tudo",
  texto:"Objetivos, histórico, pontos e conta serão apagados deste aparelho.",
  botoes:[{r:"Apagar tudo",c:"btn-vermelho",f:async()=>{
    if(T.rodando) pausar(true);
    fecharPiP(); T.itemId=null;
    await apagarTudo(); T.itemId=null;
    salvar(true); ir("login"); aviso("Tudo apagado.");
  }},{r:"Cancelar",c:"btn-cinza"}]});
$("#b-sair").onclick=()=>{ if(T.rodando) pausar(true); fecharPiP(); T.itemId=null; E.logado=false; salvar(true); ir("login"); };


document.addEventListener("visibilitychange",()=>{
  if(!T.rodando) return;
  // o tempo real continua valendo: ao voltar, o próprio tique aplica o intervalo passado
  if(document.hidden){ descarregar(); salvar(true); }
  else tique();
});
function despedida(){ if(T.rodando) descarregar(); Store.gravar(CHAVE, E); }
window.addEventListener("pagehide", despedida);
window.addEventListener("beforeunload", despedida);

/* vira o dia sozinho enquanto o app fica aberto */
setInterval(()=>{ if(virarPeriodos()) renderTudo(); }, 60000);

/* Fechar o modal pelo veu ou pelo Esc. */
$("#veu").addEventListener("click", e=>{ if(e.target.id==="veu") fecharModal(); });
document.addEventListener("keydown", e=>{
  if(e.key!=="Escape") return;
  if($("#veu").classList.contains("on")){ fecharModal(); return; }
  if($("#foco").classList.contains("on")) fecharFoco();
});

ativarArrasto();

/* ---------- Partida ---------- */
async function iniciar(){
  await carregar();

  /* Completa campos que versoes antigas do estado nao tinham, para um
     backup de meses atras nao quebrar a tela ao ser reaberto. */
  {
    if(!Array.isArray(E.itens)) E.itens=[];
    if(!E.hist || typeof E.hist!=="object") E.hist={};
    // completa objetivos gravados por versões antigas
    E.itens.forEach(it=>{
      it.feito = it.feito||0; it.saldo = it.saldo||0; it.progresso = it.progresso||0;
      it.cat = it.cat||"Outro"; it.status = it.status||"andamento";
      if(!it.periodoRef) it.periodoRef = chavePeriodo(it.freq, hoje());
    });
  }
  if(E.logado && !E.usuario) E.logado=false;
  virarPeriodos();
  limparForm();
  if(E.logado && E.usuario){ ir("home"); }
  else{
    if(E.usuario) $("#in-email").value = E.usuario.email||"";
    ir("login");
  }
}

iniciar();
