/* Atalhos de consulta ao DOM. */

export const $  = s => document.querySelector(s);
export const $$ = s => Array.from(document.querySelectorAll(s));

/* Seleciona a opcao de um <select> tolerando diferenca de acento e
   caixa — o valor guardado pode vir de uma versao antiga do app. */
export function definirSelect(sel, valor){
  const el = $(sel); if(!el) return;
  if(valor==null || valor==="") return;
  const existe = Array.from(el.options).some(o=>o.value===valor || o.text===valor);
  if(!existe){ const o=document.createElement("option"); o.textContent=valor; el.appendChild(o); }
  el.value = valor;
}
