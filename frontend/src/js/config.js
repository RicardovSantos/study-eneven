/* Configuração do front-end.

   VITE_API_URL define onde a API vive. Vazio significa "sem servidor":
   o app continua funcionando com os dados locais, como sempre funcionou.

   Isso não é gambiarra — é o que permite migrar sem apagão. Enquanto o
   backend não estiver publicado (Fase 7), o site continua no ar em modo
   local; quando estiver, uma variável de ambiente no build liga tudo. */

export const API_URL = (import.meta.env?.VITE_API_URL || "").replace(/\/$/, "");

/* Verdadeiro quando existe servidor configurado. */
export const COM_SERVIDOR = API_URL.length > 0;

export const CHAVE_ESTADO_LOCAL = "devlog:estado:v1";
