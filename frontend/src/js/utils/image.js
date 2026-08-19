/* Le a foto escolhida, reduz e comprime no proprio navegador antes
   de guardar: sem isso uma foto de celular viraria varios MB de
   base64 dentro do estado. */

import { E, salvar } from "../stores/app-store.js";
import { aviso } from "../components/toast.js";
import { emitir, EVENTOS } from "../core/bus.js";

export function lerFoto(arq){
  if(!E.usuario){ aviso("Entre na sua conta para trocar a foto."); return; }
  if(!/^image\//.test(arq.type||"")){ aviso("Escolha um arquivo de imagem."); return; }
  const fr=new FileReader();
  fr.onerror=()=>aviso("Não foi possível ler essa imagem.");
  fr.onload = ev=>{
    const img=new Image();
    img.onload=()=>{
      if(!E.usuario) return;
      const lado=Math.min(img.width,img.height);
      const cv=document.createElement("canvas"); cv.width=cv.height=280;
      const cx=cv.getContext("2d");
      cx.drawImage(img,(img.width-lado)/2,(img.height-lado)/2,lado,lado,0,0,280,280);
      E.usuario.foto = cv.toDataURL("image/jpeg",.82);
      salvar(true); emitir(EVENTOS.REDESENHAR); aviso("Foto atualizada.");
    };
    img.onerror=()=>aviso("Não foi possível ler essa imagem.");
    img.src=ev.target.result;
  };
  fr.readAsDataURL(arq);
}
