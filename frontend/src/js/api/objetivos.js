/* Objetivos e ocorrências. */

import { api } from "./client.js";

export const listar = (params = {}) => {
  const q = new URLSearchParams(params).toString();
  return api.get(`/api/v1/objetivos${q ? `?${q}` : ""}`);
};

export const criar = (dados) => api.post("/api/v1/objetivos", dados);
export const editar = (id, dados) => api.patch(`/api/v1/objetivos/${id}`, dados);
export const excluir = (id) => api.delete(`/api/v1/objetivos/${id}`);

export const ocorrencias = (params = {}) => {
  const q = new URLSearchParams(params).toString();
  return api.get(`/api/v1/ocorrencias${q ? `?${q}` : ""}`);
};

export const registrarProgresso = (id, quantidade) =>
  api.post(`/api/v1/ocorrencias/${id}/progresso`, { quantidade });

export const concluir = (id, dados = {}) =>
  api.post(`/api/v1/ocorrencias/${id}/concluir`, dados);

export const desfazer = (id) => api.post(`/api/v1/ocorrencias/${id}/desfazer`);

export const proxima = (id) => api.get(`/api/v1/ocorrencias/${id}/proxima`);
