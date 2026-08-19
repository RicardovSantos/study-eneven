/* Sessões de estudo.

   O heartbeat é o que mantém o tempo correndo no servidor. Sem ele, o
   servidor considera a sessão interrompida depois de 90 segundos — e
   com razão: não há como saber se o aparelho ainda está lá. */

import { api } from "./client.js";

export const INTERVALO_HEARTBEAT_MS = 30_000;

export const abrir = (dados) => api.post("/api/v1/sessoes", dados);
export const aberta = () => api.get("/api/v1/sessoes/aberta");
export const obter = (id) => api.get(`/api/v1/sessoes/${id}`);

export const heartbeat = (id, estado = {}) =>
  api.post(`/api/v1/sessoes/${id}/heartbeat`, {
    capturando: !!estado.capturando,
    localizando: !!estado.localizando,
  });

export const pausar = (id) => api.post(`/api/v1/sessoes/${id}/pausar`);
export const retomar = (id) => api.post(`/api/v1/sessoes/${id}/retomar`);

export const finalizar = (id, dados = {}) =>
  api.post(`/api/v1/sessoes/${id}/finalizar`, dados);

/* Mantém o heartbeat batendo enquanto a sessão estiver aberta.
   Devolve a função que para o ciclo. */
export function manterVivo(sessaoId, aoResponder) {
  const id = setInterval(async () => {
    try {
      const r = await heartbeat(sessaoId);
      aoResponder?.(r);
    } catch (e) {
      // Falha de rede não derruba o ciclo: a próxima batida tenta de novo.
      console.warn("heartbeat falhou", e.message);
    }
  }, INTERVALO_HEARTBEAT_MS);
  return () => clearInterval(id);
}
