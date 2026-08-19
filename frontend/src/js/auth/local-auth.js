/* Autenticacao — local ou pela API, conforme COM_SERVIDOR.

   Os nomes exportados (entrar, criarConta, recuperar) e os ids do DOM
   que leem/escrevem sao os mesmos nos dois modos: app.js liga os
   eventos uma vez só, sem saber qual caminho vai rodar.

   MODO LOCAL — PROVISORIO: guarda a senha em texto puro no
   armazenamento do navegador e compara no cliente. A senha gravada
   aqui NUNCA deve ser importada para o sistema real (secao 18 da
   especificacao).

   MODO API: delega para app/js/api/auth.js — Argon2 no servidor, JWT
   de vida curta e refresh token em cookie HttpOnly. */

import { $ } from "../utils/dom.js";
import { E, salvar } from "../stores/app-store.js";
import { esc } from "../utils/format.js";
import { modal } from "../components/modal.js";
import { ir } from "../router.js";
import { emitir, EVENTOS } from "../core/bus.js";
import { COM_SERVIDOR } from "../config.js";
import * as authApi from "../api/auth.js";
import { ErroDaApi } from "../api/client.js";

/* Espelha o usuário autenticado pela API no formato que as telas (Home,
   Perfil) já leem de E.usuario. Nenhum dado sensível é gravado aqui —
   a sessão de verdade vive no cookie HttpOnly e no token em memória. */
function espelharUsuario(usuario, { familiaId, papel } = {}){
  E.usuario = {
    id: usuario.id, nome: usuario.nome_exibicao, email: usuario.email,
    foto: usuario.avatar_caminho || null,
  };
  E.logado = true;
  E.online = true;
  E.familiaId = familiaId ?? E.familiaId ?? null;
  E.papel = papel ?? E.papel ?? null;
}

function mensagemDeErro(e, generica){
  return e instanceof ErroDaApi ? e.message : generica;
}

export async function entrar(){
  if(COM_SERVIDOR){
    const identificador = $("#in-email").value.trim();
    const senha = $("#in-senha").value;
    try{
      const r = await authApi.entrar({ identificador, senha });
      $("#erro-login").textContent="";
      $("#in-senha").value="";
      espelharUsuario(r.usuario, { familiaId: r.familia_id, papel: r.papel });
      ir("home");
    }catch(e){
      $("#erro-login").textContent = mensagemDeErro(e, "Não deu para entrar. Confira sua conexão.");
    }
    return;
  }
  const em=$("#in-email").value.trim().toLowerCase(), se=$("#in-senha").value;
  if(!E.usuario){ $("#erro-login").textContent="Nenhuma conta neste aparelho. Cadastre-se primeiro."; return; }
  if(em!==(E.usuario.email||"").toLowerCase() || se!==E.usuario.senha){
    $("#erro-login").textContent="Email ou senha não conferem."; return;
  }
  $("#erro-login").textContent=""; $("#in-senha").value="";
  E.logado=true; salvar(true); ir("home");
}

export async function criarConta(){
  const nome=$("#cad-nome").value.trim(), em=$("#cad-email").value.trim(),
        s1=$("#cad-senha").value, s2=$("#cad-senha2").value;
  if(nome.length<2){ $("#erro-cadastro").textContent="Escreva seu nome."; return; }
  if(!/^\S+@\S+\.\S+$/.test(em)){ $("#erro-cadastro").textContent="Email inválido."; return; }
  if(s1.length<4){ $("#erro-cadastro").textContent="A senha precisa de ao menos 4 caracteres."; return; }
  if(s1!==s2){ $("#erro-cadastro").textContent="As senhas não são iguais."; return; }
  if(!$("#cad-termos").checked){ $("#erro-cadastro").textContent="É preciso aceitar os termos."; return; }
  $("#erro-cadastro").textContent="";

  if(COM_SERVIDOR){
    // A API pede senha com letra e número — o formulário local não
    // avisava disso, então a mensagem de erro precisa ser clara aqui.
    try{
      const r = await authApi.cadastrar({ nome, email: em, senha: s1 });
      $("#cad-senha").value=""; $("#cad-senha2").value="";
      espelharUsuario(r.usuario, { familiaId: r.familia_id, papel: r.papel });
      ir("home");
      modal({selo:"ok",icone:"✓",titulo:"Conta criada",
        texto:"Bem-vindo, "+esc(nome.split(" ")[0])+".<br>Agora cadastre seus objetivos na aba Objetivos.",
        botoes:[{r:"Começar",c:"btn-verde",f:()=>ir("objetivos")},{r:"Ver o painel",c:"btn-cinza"}]});
    }catch(e){
      $("#erro-cadastro").textContent = mensagemDeErro(e, "Não deu para criar a conta. Confira sua conexão.");
    }
    return;
  }

  E.usuario={nome,email:em,senha:s1,foto:null,nasc:"",sexo:"Prefiro não informar",
    escola:"Superior",pais:"Brasil",termos:true};
  E.logado=true; salvar(true);
  $("#cad-senha").value=""; $("#cad-senha2").value="";
  ir("home");
  modal({selo:"ok",icone:"✓",titulo:"Conta criada",
    texto:"Bem-vindo, "+esc(nome.split(" ")[0])+".<br>Agora cadastre seus objetivos na aba Objetivos.",
    botoes:[{r:"Começar",c:"btn-verde",f:()=>ir("objetivos")},{r:"Ver o painel",c:"btn-cinza"}]});
}

export async function recuperar(){
  if(COM_SERVIDOR){
    // A recuperação real (token de uso único por e-mail) ainda não
    // existe no backend — ver docs/o-que-falta.md. Por ora, orienta.
    $("#erro-rec").textContent="";
    modal({selo:"info",icone:"✉",titulo:"Em construção",
      texto:"A recuperação de senha por e-mail ainda não está pronta neste servidor. "+
        "Fale com o responsável da sua família para redefinir sua senha.",
      botoes:[{r:"Voltar ao login",c:"btn-azul",f:()=>ir("login")}]});
    return;
  }
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

export async function sair(){
  if(COM_SERVIDOR){
    try{ await authApi.sair(); }catch(e){ /* mesmo se falhar, sai localmente */ }
    // Ao contrário do modo local, aqui os dados da conta não ficam
    // guardados no aparelho — a próxima entrada busca tudo de novo na API.
    E.logado=false; E.online=false; E.usuario=null;
    ir("login");
    return;
  }
  // Local: mantém E.usuario (o e-mail/senha salvos) para o próximo login
  // neste aparelho continuar funcionando — só desloga a sessão atual.
  E.logado=false; salvar(true); ir("login");
}

/* Chamado na partida quando há servidor: tenta retomar a sessão pelo
   cookie de refresh (HttpOnly, não lido aqui, só usado pelo navegador).
   Devolve true se conseguiu. */
export async function tentarSessaoOnline(){
  try{
    const r = await authApi.sessaoAtual();
    espelharUsuario(r.usuario, { familiaId: r.familia_id, papel: r.papel });
    return true;
  }catch(e){
    return false;
  }
}
