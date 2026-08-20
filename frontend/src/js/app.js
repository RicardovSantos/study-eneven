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
import { esc } from "./utils/format.js";
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
import { entrar, criarConta, recuperar, sair, tentarSessaoOnline } from "./auth/local-auth.js";
import { lerFoto } from "./utils/image.js";
import { carregarDemo } from "./utils/demo.js";
import { exportarBackup } from "./utils/backup.js";
import { COM_SERVIDOR } from "./config.js";
import * as objetivosApi from "./api/objetivos.js";
import { criarDependente } from "./api/auth.js";
import {
  sincronizarFamilia, sincronizarRecompensas, sincronizarObjetivosCrud, sincronizarProgresso,
} from "./dados/online.js";
import { renderFamilia } from "./pages/familia.js";
import { renderRecompensas } from "./pages/recompensas.js";
import { renderMaterias } from "./pages/materias.js";
import { renderProgresso } from "./pages/progresso.js";
import { ofereceAdiantar } from "./services/adiantamento.js";
import * as painelApi from "./api/painel.js";
import * as materiasApi from "./api/materias.js";
import { ErroDaApi } from "./api/client.js";

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
  texto: COM_SERVIDOR
    ? "Fale com o responsável da sua família para redefinir sua senha ou recuperar o acesso."
    : "O DevLog roda inteiro no seu aparelho, sem servidor e sem cadastro remoto.<br><br>"+
      "Se você esqueceu o email da conta, use <b>Apagar tudo</b> na aba Perfil e comece de novo — "+
      "exporte os dados antes, se quiser guardar o histórico.",
  botoes:[{r:"Entendi",c:"btn-azul"}]});
$$("[data-voltar-login]").forEach(b=>b.onclick=()=>ir("login"));

["#p-tipo","#p-freq","#p-acum","#p-adianta"].forEach(sel=>{
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

async function atualizarMaterias(){ await sincronizarObjetivosCrud(); renderCrud(); renderMaterias(); }

$("#b-criar-materia").onclick = async ()=>{
  const nome = $("#materia-nome").value.trim();
  if(!nome){ $("#erro-materia").textContent="Escreva o nome da matéria."; return; }
  $("#erro-materia").textContent="";
  try{
    await materiasApi.criar({ nome });
    $("#materia-nome").value = "";
    await atualizarMaterias();
    aviso("Matéria adicionada.");
  }catch(e2){
    $("#erro-materia").textContent = e2 instanceof ErroDaApi ? e2.message : "Não deu para adicionar. Confira sua conexão.";
  }
};

$("#lista-materias").addEventListener("click", e=>{
  const ed = e.target.closest("[data-edit-materia]");
  const del = e.target.closest("[data-del-materia]");
  if(ed){
    const materiaId = ed.dataset.editMateria;
    const atual = (E.materias||[]).find(m=>m.id===materiaId);
    modal({selo:"info",icone:"✎",titulo:"Renomear matéria",
      texto:'<div class="campo"><label for="mv-materia-nome">Nome</label>'+
        '<input id="mv-materia-nome" value="'+esc(atual?atual.nome:"")+'"></div>',
      botoes:[{r:"Salvar",c:"btn-roxo",f: async ()=>{
        const novoNome = $("#mv-materia-nome").value.trim();
        if(!novoNome) return;
        try{
          await materiasApi.editar(materiaId, { nome: novoNome });
          await atualizarMaterias();
          aviso("Matéria renomeada.");
        }catch(e2){
          aviso(e2 instanceof ErroDaApi ? e2.message : "Não deu para renomear. Confira sua conexão.");
        }
      }},{r:"Cancelar",c:"btn-cinza"}]});
    setTimeout(()=>$("#mv-materia-nome")?.focus(),0);
    return;
  }
  if(del){
    const materiaId = del.dataset.delMateria;
    const atual = (E.materias||[]).find(m=>m.id===materiaId);
    modal({selo:"perigo",icone:"🗑",titulo:"Arquivar matéria",
      texto:"<b>"+esc(atual?atual.nome:"")+"</b> some da lista de matérias, mas os objetivos já cadastrados com ela continuam mostrando o nome.",
      botoes:[{r:"Arquivar",c:"btn-vermelho",f: async ()=>{
        try{
          await materiasApi.arquivar(materiaId);
          await atualizarMaterias();
          aviso("Matéria arquivada.");
        }catch(e2){
          aviso(e2 instanceof ErroDaApi ? e2.message : "Não deu para arquivar. Confira sua conexão.");
        }
      }},{r:"Cancelar",c:"btn-cinza"}]});
  }
});

$("#b-mais-historico").onclick = async ()=>{
  try{ await sincronizarProgresso({ continuar: true }); renderProgresso(); }
  catch(e2){ aviso(e2 instanceof ErroDaApi ? e2.message : "Não deu para carregar mais. Confira sua conexão."); }
};

$("#b-add-dependente").onclick = async ()=>{
  const nome = $("#fam-nome").value.trim();
  const username = $("#fam-username").value.trim().toLowerCase();
  const parentesco = $("#fam-parentesco").value.trim();
  const senha = $("#fam-senha").value;
  if(nome.length<2){ $("#erro-familia").textContent="Escreva o nome do dependente."; return; }
  if(username.length<3){ $("#erro-familia").textContent="O usuário precisa de ao menos 3 caracteres."; return; }
  if(senha.length<8 || /^\d+$/.test(senha) || /^[a-zA-Z]+$/.test(senha)){
    $("#erro-familia").textContent="A senha precisa de ao menos 8 caracteres, com letra e número."; return;
  }
  $("#erro-familia").textContent="";
  try{
    await criarDependente({
      nome_exibicao: nome, username, senha_temporaria: senha,
      parentesco: parentesco || null,
    });
    $("#fam-nome").value=""; $("#fam-username").value="";
    $("#fam-parentesco").value=""; $("#fam-senha").value="";
    await sincronizarFamilia(); renderFamilia();
    modal({selo:"ok",icone:"✓",titulo:"Dependente cadastrado",
      texto:"Anote o usuário e a senha temporária para repassar a ele: <b>"+esc(username)+"</b>.",
      botoes:[{r:"OK",c:"btn-verde"}]});
  }catch(e){
    $("#erro-familia").textContent = e instanceof ErroDaApi ? e.message : "Não deu para cadastrar. Confira sua conexão.";
  }
};

async function atualizarRecompensas(){ await sincronizarRecompensas(); renderRecompensas(); }

$("#rec-quem").addEventListener("click", async e=>{
  const b = e.target.closest("[data-quem]"); if(!b) return;
  E.recompensasBeneficiario = { id: b.dataset.quem, nome: b.dataset.nome };
  try{ await atualizarRecompensas(); }
  catch(e2){ aviso(e2 instanceof ErroDaApi ? e2.message : "Não deu para atualizar. Confira sua conexão."); }
});

$("#b-criar-trilha").onclick = async ()=>{
  const nome = $("#rec-trilha-nome").value.trim();
  if(!nome) return;
  try{
    await painelApi.criarTrilha({ nome, beneficiario_id: E.recompensasBeneficiario?.id });
    $("#rec-trilha-nome").value = "";
    await atualizarRecompensas();
    aviso("Trilha criada.");
  }catch(e2){
    aviso(e2 instanceof ErroDaApi ? e2.message : "Não deu para criar a trilha. Confira sua conexão.");
  }
};

$("#lista-trilhas").addEventListener("click", e=>{
  const b = e.target.closest("[data-add-nivel]"); if(!b) return;
  const trilhaId = b.dataset.addNivel;
  modal({selo:"info",icone:"🏆",titulo:"Adicionar nível",
    texto:'<div class="campo"><label for="mv-pontos">Pontos necessários</label>'+
      '<input id="mv-pontos" type="number" min="1" step="1"></div>'+
      '<div class="campo"><label for="mv-premio">Prêmio</label>'+
      '<input id="mv-premio" placeholder="Ex.: Uma sobremesa"></div>',
    botoes:[{r:"Adicionar",c:"btn-roxo",f: async ()=>{
      const pontos = parseInt($("#mv-pontos").value, 10);
      const premio = $("#mv-premio").value.trim();
      if(!(pontos>0) || !premio){ aviso("Preencha os pontos e o prêmio."); return; }
      try{
        await painelApi.adicionarNivel(trilhaId, { pontos_necessarios: pontos, premio });
        await atualizarRecompensas();
        aviso("Nível adicionado.");
      }catch(e2){
        aviso(e2 instanceof ErroDaApi ? e2.message : "Não deu para adicionar o nível. Confira sua conexão.");
      }
    }},{r:"Cancelar",c:"btn-cinza"}]});
  setTimeout(()=>$("#mv-pontos")?.focus(),0);
});

$("#lista-premios").addEventListener("click", async e=>{
  const sol = e.target.closest("[data-solicitar]");
  const ent = e.target.closest("[data-entregar]");
  if(!sol && !ent) return;
  try{
    if(sol) await painelApi.solicitarPremio(sol.dataset.solicitar);
    if(ent) await painelApi.confirmarEntrega(ent.dataset.entregar);
    await atualizarRecompensas();
    aviso(sol ? "Prêmio solicitado." : "Entrega confirmada.");
  }catch(e2){
    aviso(e2 instanceof ErroDaApi ? e2.message : "Não deu para atualizar. Confira sua conexão.");
  }
});

$("#tela-estudar").addEventListener("click", async e=>{
  const pl=e.target.closest("[data-play]");
  const ck=e.target.closest("[data-check]");
  const ma=e.target.closest("[data-mais]");
  const rb=e.target.closest("[data-reabrir]");

  if(pl){ abrirFoco(pl.dataset.play); return; }

  if(ma){
    const it=E.itens.find(x=>x.id===ma.dataset.mais); if(!it) return;
    if(restante(it)<=0){ aviso("Já concluído neste período."); return; }
    if(COM_SERVIDOR){
      try{
        await objetivosApi.registrarProgresso(it.id, 1);
        // uma unidade a mais pode ter batido a meta: pergunta ao servidor
        // se ja pode concluir (ele e quem calcula pontos e credita).
        const atualizado = (await objetivosApi.ocorrencias()).find(o=>o.id===it.id);
        if(atualizado && atualizado.realizado>=atualizado.meta){
          const r = await objetivosApi.concluir(it.id, {});
          bip(920,.3); aviso("Concluído! +"+r.pontos_creditados+" pontos");
          await ofereceAdiantar(it.id, it.nome);
        }
        renderTudo();
      }catch(e2){
        aviso(e2 instanceof ErroDaApi ? e2.message : "Não deu para marcar. Confira sua conexão.");
      }
      return;
    }
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
    if(COM_SERVIDOR){
      try{
        if(restante(it)<=0){
          await objetivosApi.desfazer(it.id);
          aviso("Reaberto.");
        }else{
          const r = await objetivosApi.concluir(it.id, {});
          bip(920,.3);
          aviso(r.pontos_creditados>0 ? "Concluído! +"+r.pontos_creditados+" pontos" : "Concluído.");
          await ofereceAdiantar(it.id, it.nome);
        }
        renderTudo();
      }catch(e2){
        aviso(e2 instanceof ErroDaApi ? e2.message : "Não deu para atualizar. Confira sua conexão.");
      }
      return;
    }
    if(restante(it)<=0) desfazerCiclo(it); else concluirCiclo(it,true);
    return;
  }

  if(rb){
    // "Reabrir" na lista de concluídos só existe no modo local — na API
    // o mesmo botão de check (data-check) já reabre a ocorrência.
    if(COM_SERVIDOR) return;
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
  if(COM_SERVIDOR){
    // Ainda não existe endpoint para editar o próprio perfil (nome,
    // e-mail, senha) — ver docs/o-que-falta.md. Fingir que salvou
    // localmente enganaria: o próximo login mostraria os dados antigos.
    $("#erro-perfil").textContent="";
    modal({selo:"info",icone:"⚙",titulo:"Em construção",
      texto:"Editar o perfil ainda não está disponível neste servidor.",
      botoes:[{r:"Entendi",c:"btn-azul"}]});
    return;
  }
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
$("#b-demo").onclick=()=>{
  if(COM_SERVIDOR){
    modal({selo:"info",icone:"⚙",titulo:"Em construção",
      texto:"Carregar dados de exemplo ainda não está disponível neste servidor. "+
        "Cadastre seus objetivos de verdade na aba Objetivos.",
      botoes:[{r:"Entendi",c:"btn-azul"}]});
    return;
  }
  modal({selo:"info",icone:"⚙",titulo:"Carregar exemplo",
    texto:"Isso substitui seus objetivos e o histórico por dados de demonstração.",
    botoes:[{r:"Carregar",c:"btn-roxo",f:carregarDemo},{r:"Cancelar",c:"btn-cinza"}]});
};
$("#b-exportar").onclick=exportarBackup;
$("#b-zerar").onclick=()=>{
  if(COM_SERVIDOR){
    modal({selo:"info",icone:"⚙",titulo:"Em construção",
      texto:"Apagar a conta ainda não está disponível por aqui. Fale com o responsável da sua família.",
      botoes:[{r:"Entendi",c:"btn-azul"}]});
    return;
  }
  modal({selo:"perigo",icone:"🗑",titulo:"Apagar tudo",
    texto:"Objetivos, histórico, pontos e conta serão apagados deste aparelho.",
    botoes:[{r:"Apagar tudo",c:"btn-vermelho",f:async()=>{
      if(T.rodando) pausar(true);
      fecharPiP(); T.itemId=null;
      await apagarTudo(); T.itemId=null;
      salvar(true); ir("login"); aviso("Tudo apagado.");
    }},{r:"Cancelar",c:"btn-cinza"}]});
};
$("#b-sair").onclick=async ()=>{
  if(T.rodando) await pausar(true);
  fecharPiP(); T.itemId=null;
  await sair();
};


document.addEventListener("visibilitychange",()=>{
  if(!T.rodando) return;
  // o tempo real continua valendo: ao voltar, o próprio tique aplica o intervalo passado
  if(document.hidden){ descarregar(); if(!COM_SERVIDOR) salvar(true); }
  else tique();
});
function despedida(){ if(T.rodando) descarregar(); if(!COM_SERVIDOR) Store.gravar(CHAVE, E); }
window.addEventListener("pagehide", despedida);
window.addEventListener("beforeunload", despedida);

/* Vira o dia sozinho enquanto o app fica aberto. Com servidor, quem
   decide se algo venceu é a própria API a cada consulta — então aqui
   basta redesenhar, que já dispara a busca fresca (ver pages/index.js). */
setInterval(()=>{
  if(COM_SERVIDOR) renderTudo();
  else if(virarPeriodos()) renderTudo();
}, 60000);

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
  limparForm();

  if(COM_SERVIDOR){
    // Sem localStorage aqui: a sessão de verdade vive no cookie de
    // refresh (HttpOnly) e no token em memória, nunca no navegador em
    // texto legível por script.
    const retomou = await tentarSessaoOnline();
    ir(retomou ? "home" : "login");
    return;
  }

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
  if(E.logado && E.usuario){ ir("home"); }
  else{
    if(E.usuario) $("#in-email").value = E.usuario.email||"";
    ir("login");
  }
}

iniciar();
