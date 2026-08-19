/* Tela Perfil: dados da conta, foto, exportacao e acoes destrutivas. */

import { $, definirSelect } from "../utils/dom.js";
import { E } from "../stores/app-store.js";
import { Store } from "../stores/storage.js";
import { fotoOu } from "../utils/avatar.js";

export function renderPerfil(){
  const u=E.usuario||{};
  $("#pf-foto").src = fotoOu(u);
  $("#pf-nome").value=u.nome||""; $("#pf-email").value=u.email||"";
  $("#pf-senha").value="";                 // nunca devolve a senha para a tela
  $("#pf-nasc").value=u.nasc||"";
  definirSelect("#pf-sexo", u.sexo);
  definirSelect("#pf-escola", u.escola);
  definirSelect("#pf-pais", u.pais);
  $("#pf-termos").checked=!!u.termos;
  $("#pf-armazenamento").textContent =
    "Salvo em: "+Store.modo+". "+E.itens.length+" objetivo(s), "+
    Object.keys(E.hist).length+" dia(s) de histórico, "+E.pontos+" pontos.";
}
