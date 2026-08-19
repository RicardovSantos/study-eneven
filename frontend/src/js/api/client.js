/* Cliente HTTP da API.

   Duas responsabilidades que não valem repetir em cada chamada:

   1. **Renovar o token sozinho.** O access token dura 15 minutos. Quando
      uma chamada volta 401, o cliente tenta `/auth/renovar` (que usa o
      cookie HttpOnly) e repete a chamada original. O usuário não é
      deslogado no meio de uma sessão de estudo por causa disso.

   2. **Não deixar duas renovações correrem juntas.** Se três chamadas
      falharem ao mesmo tempo, uma única renovação acontece e as outras
      esperam por ela — senão a segunda invalidaria o token que a
      primeira acabou de emitir (o refresh é rotativo). */

import { API_URL } from "../config.js";

/* O access token fica só em memória. Guardá-lo em localStorage o
   deixaria ao alcance de qualquer script injetado na página. */
let accessToken = null;
let renovacaoEmCurso = null;

export function definirToken(token) {
  accessToken = token || null;
}

export function temToken() {
  return accessToken !== null;
}

export class ErroDaApi extends Error {
  constructor(status, detalhe, corpo) {
    super(detalhe || `Erro ${status}`);
    this.name = "ErroDaApi";
    this.status = status;
    this.corpo = corpo;
  }
}

function mensagemDoErro(corpo, status) {
  if (!corpo) return null;
  if (typeof corpo.detail === "string") return corpo.detail;
  // 422 do FastAPI vem como lista de problemas por campo
  if (Array.isArray(corpo.detail)) {
    return corpo.detail
      .map((p) => p.msg?.replace(/^Value error, /, ""))
      .filter(Boolean)
      .join(" · ");
  }
  return `Erro ${status}`;
}

async function enviar(metodo, caminho, corpo, { semRenovar = false } = {}) {
  const resposta = await fetch(API_URL + caminho, {
    method: metodo,
    headers: {
      ...(corpo !== undefined ? { "Content-Type": "application/json" } : {}),
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    },
    // O refresh token viaja em cookie HttpOnly; sem isto ele não é enviado.
    credentials: "include",
    ...(corpo !== undefined ? { body: JSON.stringify(corpo) } : {}),
  });

  if (resposta.status === 401 && !semRenovar) {
    const renovou = await renovar();
    if (renovou) return enviar(metodo, caminho, corpo, { semRenovar: true });
  }

  if (resposta.status === 204) return null;

  let dados = null;
  try {
    dados = await resposta.json();
  } catch {
    dados = null;
  }

  if (!resposta.ok) {
    throw new ErroDaApi(resposta.status, mensagemDoErro(dados, resposta.status), dados);
  }
  return dados;
}

/* Renova o par de tokens. Devolve true se conseguiu.

   A promessa é compartilhada: chamadas simultâneas esperam a mesma
   renovação em vez de dispararem várias, o que invalidaria umas às
   outras por causa da rotação. */
export function renovar() {
  if (renovacaoEmCurso) return renovacaoEmCurso;

  renovacaoEmCurso = (async () => {
    try {
      const dados = await enviar("POST", "/api/v1/auth/renovar", undefined, {
        semRenovar: true,
      });
      definirToken(dados.access_token);
      return true;
    } catch {
      definirToken(null);
      return false;
    } finally {
      renovacaoEmCurso = null;
    }
  })();

  return renovacaoEmCurso;
}

export const api = {
  get: (caminho) => enviar("GET", caminho),
  post: (caminho, corpo) => enviar("POST", caminho, corpo ?? {}),
  patch: (caminho, corpo) => enviar("PATCH", caminho, corpo),
  delete: (caminho) => enviar("DELETE", caminho),
};
