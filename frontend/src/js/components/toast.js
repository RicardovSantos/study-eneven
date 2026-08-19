/* Tarja de aviso no topo. Fica escondida por opacity/visibility,
   nunca por deslocamento em % da propria altura: vazia ela mede
   poucos pixels e reaparecia por cima da navegacao. */

import { $ } from "../utils/dom.js";

let avisoTimer = null;

export function aviso(txt){
  const el=$("#aviso"); el.textContent=txt; el.classList.add("on");
  clearTimeout(avisoTimer); avisoTimer=setTimeout(()=>el.classList.remove("on"),2600);
}
