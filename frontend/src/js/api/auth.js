/* Autenticação pela API. */

import { api, definirToken } from "./client.js";

export async function cadastrar({ nome, email, senha, username, nomeFamilia }) {
  const dados = await api.post("/api/v1/auth/cadastrar", {
    nome_exibicao: nome,
    username: username || email.split("@")[0].toLowerCase().replace(/[^a-z0-9._]/g, ""),
    email,
    senha,
    nome_familia: nomeFamilia || `Família de ${nome.split(" ")[0]}`,
  });
  definirToken(dados.access_token);
  return dados;
}

export async function entrar({ identificador, senha }) {
  const dados = await api.post("/api/v1/auth/entrar", { identificador, senha });
  definirToken(dados.access_token);
  return dados;
}

/* Tenta retomar uma sessão existente pelo cookie de refresh (HttpOnly),
   sem exigir login de novo. Devolve o par completo (usuario, familia_id,
   papel), diferente de client.renovar() — que só devolve um booleano e
   serve ao retry automático de 401, não à partida do app.

   semRenovar:true é essencial aqui: sem isso, um primeiro acesso (sem
   cookie ainda) devolve 401 e o cliente tentaria renovar de novo por
   cima dessa própria chamada de renovação — dois POSTs em /auth/renovar
   para o mesmo 401 esperado de "ainda não tem sessão". */
export async function sessaoAtual() {
  const dados = await api.post("/api/v1/auth/renovar", undefined, { semRenovar: true });
  definirToken(dados.access_token);
  return dados;
}

export async function sair() {
  try {
    await api.post("/api/v1/auth/sair");
  } finally {
    definirToken(null);
  }
}

export const eu = () => api.get("/api/v1/auth/eu");

export const criarDependente = (dados) =>
  api.post("/api/v1/auth/dependentes", dados);

export const redefinirSenhaDependente = (id, senhaNova) =>
  api.post(`/api/v1/auth/dependentes/${id}/redefinir-senha`, { senha_nova: senhaNova });

export const desativarDependente = (id) =>
  api.post(`/api/v1/auth/dependentes/${id}/desativar`);

export const reativarDependente = (id) =>
  api.post(`/api/v1/auth/dependentes/${id}/reativar`);
