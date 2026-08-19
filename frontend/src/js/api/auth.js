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
