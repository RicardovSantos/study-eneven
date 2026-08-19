/* Autenticacao local — PROVISORIA.

   ATENCAO: guarda a senha em texto puro no armazenamento do
   navegador e compara no cliente. Serve so enquanto nao existe
   servidor; a Fase 2 substitui este arquivo inteiro por Argon2 no
   backend com token JWT. A senha gravada aqui NUNCA deve ser
   importada para o sistema real (secao 18 da especificacao). */

import { $ } from "../utils/dom.js";
import { E, salvar } from "../stores/app-store.js";
import { esc } from "../utils/format.js";
import { modal } from "../components/modal.js";
import { ir } from "../router.js";
import { emitir, EVENTOS } from "../core/bus.js";

export function entrar(){
  const em=$("#in-email").value.trim().toLowerCase(), se=$("#in-senha").value;
  if(!E.usuario){ $("#erro-login").textContent="Nenhuma conta neste aparelho. Cadastre-se primeiro."; return; }
  if(em!==(E.usuario.email||"").toLowerCase() || se!==E.usuario.senha){
    $("#erro-login").textContent="Email ou senha não conferem."; return;
  }
  $("#erro-login").textContent=""; $("#in-senha").value="";
  E.logado=true; salvar(true); ir("home");
}
export function criarConta(){
  const nome=$("#cad-nome").value.trim(), em=$("#cad-email").value.trim(),
        s1=$("#cad-senha").value, s2=$("#cad-senha2").value;
  if(nome.length<2){ $("#erro-cadastro").textContent="Escreva seu nome."; return; }
  if(!/^\S+@\S+\.\S+$/.test(em)){ $("#erro-cadastro").textContent="Email inválido."; return; }
  if(s1.length<4){ $("#erro-cadastro").textContent="A senha precisa de ao menos 4 caracteres."; return; }
  if(s1!==s2){ $("#erro-cadastro").textContent="As senhas não são iguais."; return; }
  if(!$("#cad-termos").checked){ $("#erro-cadastro").textContent="É preciso aceitar os termos."; return; }
  $("#erro-cadastro").textContent="";
  E.usuario={nome,email:em,senha:s1,foto:null,nasc:"",sexo:"Prefiro não informar",
    escola:"Superior",pais:"Brasil",termos:true};
  E.logado=true; salvar(true);
  $("#cad-senha").value=""; $("#cad-senha2").value="";
  ir("home");
  modal({selo:"ok",icone:"✓",titulo:"Conta criada",
    texto:"Bem-vindo, "+esc(nome.split(" ")[0])+".<br>Agora cadastre seus objetivos na aba Objetivos.",
    botoes:[{r:"Começar",c:"btn-verde",f:()=>ir("objetivos")},{r:"Ver o painel",c:"btn-cinza"}]});
}
export function recuperar(){
  const em=$("#rec-email").value.trim().toLowerCase(), nova=$("#rec-nova").value;
  if(!E.usuario || em!==(E.usuario.email||"").toLowerCase()){
    $("#erro-rec").textContent="Email não encontrado neste aparelho."; return; }
  if(nova.length<4){ $("#erro-rec").textContent="A nova senha precisa de ao menos 4 caracteres."; return; }
  $("#erro-rec").textContent="";
  E.usuario.senha=nova; salvar(true);
  $("#rec-nova").value="";
  modal({selo:"info",icone:"✉",titulo:"Enviado",
    texto:"Sua nova senha já está valendo. Faça o login para continuar.",
    botoes:[{r:"OK",c:"btn-azul",f:()=>ir("login")}]});
}
