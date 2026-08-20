/* Painéis, histórico e recompensas. */

import { api } from "./client.js";

export const pessoal = () => api.get("/api/v1/dashboard");
export const familia = () => api.get("/api/v1/dashboard/familia");

export const historico = ({ limite = 10, deslocamento = 0, titularId } = {}) => {
  const p = new URLSearchParams({ limite, deslocamento });
  if (titularId) p.set("titular_id", titularId);
  return api.get(`/api/v1/historico?${p}`);
};

export const recompensas = (beneficiarioId) => {
  const q = beneficiarioId ? `?beneficiario_id=${beneficiarioId}` : "";
  return api.get(`/api/v1/recompensas${q}`);
};

export const premios = (beneficiarioId) => {
  const q = beneficiarioId ? `?beneficiario_id=${beneficiarioId}` : "";
  return api.get(`/api/v1/recompensas/premios${q}`);
};

export const criarTrilha = (dados) => api.post("/api/v1/recompensas/trilhas", dados);

export const adicionarNivel = (trilhaId, dados) =>
  api.post(`/api/v1/recompensas/trilhas/${trilhaId}/niveis`, dados);

export const solicitarPremio = (id) =>
  api.post(`/api/v1/recompensas/premios/${id}/solicitar`);

export const confirmarEntrega = (id) =>
  api.post(`/api/v1/recompensas/premios/${id}/entregar`);
