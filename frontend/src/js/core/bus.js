/* Barramento de eventos.

   Existe para quebrar dependencia circular: as regras de negocio
   precisam pedir "redesenhe a tela", mas nao podem importar as
   telas (que por sua vez importam as regras). Em vez disso elas
   emitem um evento, e quem desenha se inscreve na partida. */

const inscritos = new Map();

export function em(evento, ouvinte){
  if(!inscritos.has(evento)) inscritos.set(evento, new Set());
  inscritos.get(evento).add(ouvinte);
  return () => inscritos.get(evento).delete(ouvinte);
}

export function emitir(evento, dados){
  const lista = inscritos.get(evento);
  if(!lista) return;
  for(const ouvinte of lista){
    try{ ouvinte(dados); }
    catch(e){ console.error(`Falha no ouvinte de "${evento}"`, e); }
  }
}

/* Nomes dos eventos em um lugar so, para nao errar string solta. */
export const EVENTOS = {
  REDESENHAR:   "redesenhar",
  IR_PARA:      "ir-para",
  SESSAO_MUDOU: "sessao-mudou",
  ABRIR_FOCO:   "abrir-foco",
  FECHAR_PIP:   "fechar-pip"
};
