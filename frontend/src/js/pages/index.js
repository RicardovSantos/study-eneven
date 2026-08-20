/* Ponto unico de redesenho.

   O barramento nao sabe quais telas existem; este arquivo sabe. Ele
   escuta REDESENHAR e manda desenhar apenas a tela que esta aberta.

   Com servidor configurado (COM_SERVIDOR), antes de desenhar cada tela
   busca os dados frescos da API e popula E no formato que as funcoes de
   render ja sabem ler — ver dados/online.js para o porque desse
   adaptador em vez de reescrever as telas. Sem servidor, o
   comportamento e exatamente o de sempre: so le o que ja esta em E. */

import { telaAgora } from "../router.js";
import { virarPeriodos } from "../services/objetivos.js";
import { COM_SERVIDOR } from "../config.js";
import {
  sincronizarObjetivosCrud, sincronizarOcorrenciasEstudar, sincronizarPainelHome,
  sincronizarFamilia, sincronizarRecompensas,
} from "../dados/online.js";
import { E } from "../stores/app-store.js";
import { renderHome } from "./home.js";
import { renderCrud } from "./objetivos.js";
import { renderObjetivos as renderEstudar } from "./estudar.js";
import { renderFamilia } from "./familia.js";
import { renderRecompensas } from "./recompensas.js";
import { renderPerfil } from "./perfil.js";
import { em, EVENTOS } from "../core/bus.js";
import { aviso } from "../components/toast.js";

export async function renderTudo(){
  const tela = telaAgora();

  if(COM_SERVIDOR){
    try{
      if(tela === "objetivos") await sincronizarObjetivosCrud();
      if(tela === "estudar")   await sincronizarOcorrenciasEstudar();
      if(tela === "home")      await sincronizarPainelHome();
      if(tela === "familia" && E.papel === "admin") await sincronizarFamilia();
      if(tela === "recompensas") await sincronizarRecompensas();
    }catch(e){
      // Uma falha de rede não pode deixar a tela travada num "carregando"
      // silencioso: avisa e desenha com o que já estava em E.
      aviso(e.message || "Não deu para atualizar. Confira sua conexão.");
    }
  }else{
    virarPeriodos();
  }

  if(tela === "home")      renderHome();
  if(tela === "objetivos") renderCrud();
  if(tela === "estudar")   renderEstudar();
  if(tela === "familia")   renderFamilia();
  if(tela === "recompensas") renderRecompensas();
  if(tela === "perfil")    renderPerfil();
}

em(EVENTOS.REDESENHAR, renderTudo);
