import { defineConfig } from "vite";

/* O `base` sai de uma variavel de ambiente porque o mesmo build serve
   dois destinos com raizes diferentes:

   - GitHub Pages de projeto, publicado em /study-eneven/;
   - dominio proprio (devlog.eneven.com.br), publicado na raiz.

   O workflow do Pages define VITE_BASE=/study-eneven/; em qualquer
   outro lugar o padrao "/" ja esta certo. */
export default defineConfig({
  base: process.env.VITE_BASE || "/",
  build: {
    outDir: "dist",
    emptyOutDir: true,
    target: "es2020"
  },
  server: {
    port: 5173,
    host: true
  }
});
