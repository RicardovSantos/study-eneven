/* Formatacao de texto exibido e escape de conteudo do usuario. */

import { p2 } from "./dates.js";

export function fmtHM(min){
  min = Math.max(0, Math.round(min));
  const h = Math.floor(min/60), m = min%60;
  if(h && m) return h+"h "+m+"min";
  if(h) return h+"h";
  return m+"min";
}
export function fmtRelogio(seg){
  seg = Math.max(0, Math.round(seg));
  return p2(Math.floor(seg/3600))+":"+p2(Math.floor(seg%3600/60))+":"+p2(seg%60);
}
export function esc(t){ return String(t==null?"":t).replace(/[&<>"']/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }
export function id(){ return Date.now().toString(36)+Math.random().toString(36).slice(2,7); }
