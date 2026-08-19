/* Ponto unico de redesenho.

   O barramento nao sabe quais telas existem; este arquivo sabe. Ele
   escuta REDESENHAR e manda desenhar apenas a tela que esta aberta. */

import { telaAgora } from "../router.js";
import { virarPeriodos } from "../services/objetivos.js";
import { renderHome } from "./home.js";
import { renderCrud } from "./objetivos.js";
import { renderObjetivos as renderEstudar } from "./estudar.js";
import { renderPerfil } from "./perfil.js";
import { em, EVENTOS } from "../core/bus.js";

export function renderTudo(){
  virarPeriodos();
  const tela = telaAgora();
  if(tela === "home")      renderHome();
  if(tela === "objetivos") renderCrud();
  if(tela === "estudar")   renderEstudar();
  if(tela === "perfil")    renderPerfil();
}

em(EVENTOS.REDESENHAR, renderTudo);
