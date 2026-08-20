/* Depois de concluir uma ocorrência, oferece adiantar a próxima da fila
   se o objetivo permitir (permite_adiantar) e o limite não tiver
   estourado — quem decide é a API (GET /ocorrencias/{id}/proxima,
   campo pode_adiantar); aqui só pergunta e, se a pessoa topar, conclui
   a próxima também (a mesma chamada de sempre, POST .../concluir — o
   servidor detecta sozinho que é adiantamento pela data prevista).

   Só faz sentido em modo servidor: no modo local a ocorrência nunca
   existiu como linha própria, então não há "próxima" para adiantar. */

import { modal } from "../components/modal.js";
import { aviso } from "../components/toast.js";
import { esc } from "../utils/format.js";
import { emitir, EVENTOS } from "../core/bus.js";
import * as objetivosApi from "../api/objetivos.js";
import { ErroDaApi } from "../api/client.js";
import { sincronizarOcorrenciasEstudar } from "../dados/online.js";

export async function ofereceAdiantar(ocorrenciaId, nomeObjetivo){
  if(!ocorrenciaId) return;
  let proxima;
  try{ proxima = await objetivosApi.proxima(ocorrenciaId); }
  catch(e){ return; }        // bônus, não o fluxo principal — falha aqui não avisa nada
  if(!proxima.pode_adiantar || !proxima.ocorrencia) return;

  const quando = new Date(proxima.ocorrencia.prevista_para+"T00:00:00");
  const dataFmt = quando.toLocaleDateString("pt-BR");
  modal({selo:"info",icone:"⏩",titulo:"Adiantar a próxima?",
    texto:"Você pode adiantar <b>"+esc(nomeObjetivo||"a próxima atividade")+"</b>, prevista para "+dataFmt+".",
    botoes:[
      {r:"Adiantar",c:"btn-roxo",f: async ()=>{
        try{
          const r = await objetivosApi.concluir(proxima.ocorrencia.id, {});
          await sincronizarOcorrenciasEstudar();
          emitir(EVENTOS.REDESENHAR);
          aviso(r.pontos_creditados>0 ? "Adiantado! +"+r.pontos_creditados+" pontos." : "Adiantado.");
        }catch(e2){
          aviso(e2 instanceof ErroDaApi ? e2.message : "Não deu para adiantar. Confira sua conexão.");
        }
      }},
      {r:"Não, obrigado",c:"btn-cinza"}
    ]});
}
