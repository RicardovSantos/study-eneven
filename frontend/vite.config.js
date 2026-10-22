import { defineConfig } from "vite";

/* Icone do atalho no iPhone.

   Ao "Adicionar a Tela de Inicio", o Safari so usa a imagem se achar a
   tag apple-touch-icon; sem ela, o atalho mostra apenas a letra "D".
   O arquivo fica em public/apple-touch-icon.png (180x180, fundo opaco).
   A tag e injetada aqui para respeitar o `base` de cada destino
   (/study-eneven/ no Pages, "/" no dominio proprio). */
function iconeDoApp() {
  let base = "/";
  return {
    name: "devlog-icone-do-app",
    configResolved(config) {
      base = config.base;
    },
    transformIndexHtml() {
      return [
        {
          tag: "link",
          attrs: { rel: "apple-touch-icon", sizes: "180x180", href: `${base}apple-touch-icon.png` },
          injectTo: "head"
        },
        {
          tag: "meta",
          attrs: { name: "apple-mobile-web-app-title", content: "DevLog" },
          injectTo: "head"
        }
      ];
    }
  };
}

/* O `base` sai de uma variavel de ambiente porque o mesmo build serve
   dois destinos com raizes diferentes:

   - GitHub Pages de projeto, publicado em /study-eneven/;
   - dominio proprio (devlog.eneven.com.br), publicado na raiz.

   O workflow do Pages define VITE_BASE=/study-eneven/; em qualquer
   outro lugar o padrao "/" ja esta certo. */
export default defineConfig({
  base: process.env.VITE_BASE || "/",
  plugins: [iconeDoApp()],
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
