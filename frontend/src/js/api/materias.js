/* Matérias. */

import { api } from "./client.js";

export const listar = (incluirInativas) => {
  const q = incluirInativas ? "?incluir_inativas=true" : "";
  return api.get(`/api/v1/materias${q}`);
};

export const criar = (dados) => api.post("/api/v1/materias", dados);

export const editar = (id, dados) => api.patch(`/api/v1/materias/${id}`, dados);

export const arquivar = (id) => api.delete(`/api/v1/materias/${id}`);
