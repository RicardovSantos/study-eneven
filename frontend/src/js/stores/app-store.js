/* Estado da aplicacao e sua persistencia.

   Enquanto nao existe backend, este e o unico dono dos dados. Na
   Fase 2 o mesmo formato passa a vir da API, e so este arquivo
   precisa mudar: o resto do app fala com o estado por aqui. */

import { Store } from "./storage.js";

export const CHAVE = "devlog:estado:v1";

export function estadoNovo(){
  return {
    usuario:null,           // {nome,email,senha,foto,nasc,sexo,escola,pais,termos}
    logado:false,
    itens:[],
    hist:{},                // "AAAA-MM-DD": {min, tarefas, pontos}
    pontos:0,
    concluidos:0,
    versao:1
  };
}

/* `E` e o estado vivo. E exportado como binding mutavel de proposito:
   os modulos leem e escrevem nele direto, como faziam antes da
   separacao em arquivos. Trocar isso por um store imutavel e
   trabalho da Fase 2, junto com a API. */
export let E = estadoNovo();

let salvarPendente = null;
export function salvar(imediato){
  if(salvarPendente){ clearTimeout(salvarPendente); salvarPendente=null; }
  if(imediato){ Store.gravar(CHAVE, E); return; }
  salvarPendente = setTimeout(()=>{ salvarPendente=null; Store.gravar(CHAVE, E); }, 400);
}

export async function carregar(){
  const guardado = await Store.ler(CHAVE);
  if(guardado && typeof guardado === "object") E = { ...estadoNovo(), ...guardado };
  return E;
}

export async function apagarTudo(){
  await Store.apagar(CHAVE);
  E = estadoNovo();
}
