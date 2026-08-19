/* Foto do usuario, ou um avatar generico em SVG embutido — assim
   nao ha requisicao de rede nem arquivo de imagem no projeto. */

export function fotoOu(u){
  return (u && u.foto) ? u.foto :
    "data:image/svg+xml;utf8,"+encodeURIComponent(
      '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" fill="#DDDCEC"/>'+
      '<circle cx="50" cy="38" r="18" fill="#9E9BC4"/><path d="M14 96a36 36 0 0 1 72 0z" fill="#9E9BC4"/></svg>');
}
