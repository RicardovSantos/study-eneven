/* Tela Perfil: dados da conta, foto, exportacao e acoes destrutivas. */

import { $, definirSelect } from "../utils/dom.js";
import { E } from "../stores/app-store.js";
import { Store } from "../stores/storage.js";
import { fotoOu } from "../utils/avatar.js";
import { COM_SERVIDOR } from "../config.js";

export function renderPerfil(){
  const u=E.usuario||{};
  $("#pf-foto").src = fotoOu(u);
  $("#pf-nome").value=u.nome||""; $("#pf-email").value=u.email||"";
  $("#pf-senha").value="";                 // nunca devolve a senha para a tela
  $("#pf-senha-atual").value="";

  // Nascimento/sexo/escola/país/termos nunca existiram no modelo do
  // servidor — são só do protótipo local original.
  $("#campo-senha-atual").style.display = COM_SERVIDOR ? "" : "none";
  $("#campo-perfil-local").style.display = COM_SERVIDOR ? "none" : "";
  if(!COM_SERVIDOR){
    $("#pf-nasc").value=u.nasc||"";
    definirSelect("#pf-sexo", u.sexo);
    definirSelect("#pf-escola", u.escola);
    definirSelect("#pf-pais", u.pais);
    $("#pf-termos").checked=!!u.termos;
  }

  $("#pf-armazenamento").textContent = COM_SERVIDOR
    ? "Conta no servidor. "+E.pontos+" ponto(s) no total."
    : "Salvo em: "+Store.modo+". "+E.itens.length+" objetivo(s), "+
      Object.keys(E.hist).length+" dia(s) de histórico, "+E.pontos+" pontos.";
}
