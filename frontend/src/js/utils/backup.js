/* Exportacao do estado em JSON. O caminho alternativo (textarea no
   modal) existe para navegadores que bloqueiam download automatico. */

import { E } from "../stores/app-store.js";
import { esc } from "./format.js";
import { modal } from "../components/modal.js";
import { aviso } from "../components/toast.js";

export function exportarBackup(){
  const txt=JSON.stringify(E,null,2);
  try{
    const b=new Blob([txt],{type:"application/json"});
    const url=URL.createObjectURL(b);
    const a=document.createElement("a");
    a.href=url; a.download="devlog-backup.json";
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(()=>URL.revokeObjectURL(url),1500);
    aviso("Backup gerado.");
  }catch(e){
    modal({selo:"info",icone:"⇩",titulo:"Backup",
      texto:"Copie o conteúdo abaixo e guarde em um arquivo .json:<br><textarea style='width:100%;height:120px;font-size:10px' readonly>"+esc(txt)+"</textarea>",
      botoes:[{r:"Fechar",c:"btn-cinza"}]});
  }
}
