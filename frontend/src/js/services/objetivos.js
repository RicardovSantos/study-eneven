/* Regras de negocio dos objetivos: metas, acumulo de pendencia,
   virada de periodo, pontuacao, conclusao e desfazer.

   Nao toca no DOM. Quando algo muda e a tela precisa acompanhar,
   emite REDESENHAR pelo barramento em vez de chamar as telas
   diretamente — e isso que evita objetivos <-> telas virarem um
   ciclo de importacao. */

import { E, salvar } from "../stores/app-store.js";
import { hoje, chaveDia, chavePeriodo } from "../utils/dates.js";
import { esc } from "../utils/format.js";
import { bip } from "../utils/sound.js";
import { modal } from "../components/modal.js";
import { emitir, EVENTOS } from "../core/bus.js";

export function tetoAcumulo(it){
  return it.freq==="diaria" ? it.alvo*6 : it.alvo*3;   // no máximo 7 dias / 4 ciclos
}
export function alvoEfetivo(it){ return it.alvo + (it.saldo||0); }
export function restante(it){ return Math.max(0, alvoEfetivo(it) - (it.feito||0)); }
export function pontosDe(it){ return it.tipo==="estudo" ? (10 + Math.floor(alvoEfetivo(it)/6)) : 8; }

/* Vira o período: aplica (ou descarta) o que ficou pendente */
export function virarPeriodos(){
  let mudou=false;
  const agora = hoje();
  E.itens.forEach(it=>{
    const atual = chavePeriodo(it.freq, agora);
    if(it.periodoRef === atual) return;
    if(it.periodoRef){
      const pendente = Math.max(0, alvoEfetivo(it) - (it.feito||0));
      if(it.acum){
        // "pendente" já inclui o saldo antigo, então ele substitui (não soma) o saldo
        it.saldo = Math.min(tetoAcumulo(it), pendente);
      }else{
        it.saldo = 0;
      }
    }
    it.feito = 0;
    it.periodoRef = atual;
    mudou = true;
  });
  if(mudou) salvar();
  return mudou;
}

export function registrarHistorico(minutos, tarefas, pontos, dia){
  const k = dia || chaveDia();
  const h = E.hist[k] || {min:0,tarefas:0,pontos:0};
  h.min += minutos||0; h.tarefas += tarefas||0; h.pontos += pontos||0;
  E.hist[k]=h;
}

/* Soma tempo de estudo (minutos) — chamado pelo cronômetro */
export function creditarEstudo(it, minutos){
  if(minutos<=0) return;
  it.feito = (it.feito||0) + minutos;
  it.progresso = (it.progresso||0) + minutos;
  registrarHistorico(minutos,0,0);
}

/* Conclui o ciclo atual do objetivo */
export function concluirCiclo(it, comAviso){
  const pts = pontosDe(it);
  E.pontos += pts;
  E.concluidos += 1;
  // guarda o que este ciclo mudou, para o "desfazer" devolver exatamente isso
  const antes = {feito:it.feito||0, saldo:it.saldo||0, status:it.status, credito:0, pontos:pts};
  if(it.tipo==="tarefa"){
    // só o que faltava entra no total — o que veio dos cliques em "+" já foi somado
    antes.credito = restante(it);
    it.feito = alvoEfetivo(it);
    it.progresso = (it.progresso||0) + antes.credito;
  }else{
    // no estudo o total acumulado vem do cronômetro; concluir não inventa minutos
    it.feito = Math.max(it.feito||0, alvoEfetivo(it));
  }
  it.desfazer = antes;
  registrarHistorico(0,1,pts);
  it.saldo = 0;
  it.ultimaConclusao = chaveDia();
  if(it.totalMeta>0 && (it.progresso||0) >= it.totalMeta) it.status="concluido";
  salvar(true);
  if(comAviso!==false){
    bip(880,.35); setTimeout(()=>bip(1180,.5),240);
    modal({selo:"ok",icone:"✓",titulo:"Concluído",
      texto:"<b>"+esc(it.nome)+"</b><br>+"+pts+" pontos somados ao seu placar.",
      botoes:[{r:"OK",c:"btn-verde"}]});
  }
  emitir(EVENTOS.REDESENHAR);
}

/* Desmarca um objetivo concluído no ciclo, devolvendo o estado anterior */
export function desfazerCiclo(it){
  const d = it.desfazer || {};
  const pts = (d.pontos!=null) ? d.pontos : pontosDe(it);
  E.pontos = Math.max(0, E.pontos - pts);
  E.concluidos = Math.max(0, E.concluidos - 1);
  // devolve só o que a conclusão somou (no estudo isso é zero: os minutos são reais)
  it.progresso = Math.max(0, (it.progresso||0) - (d.credito||0));
  it.feito = d.feito || 0;
  it.saldo = d.saldo || 0;
  if(it.status==="concluido") it.status = d.status || "andamento";
  // desconta no dia em que a conclusão foi registrada, não sempre em "hoje"
  const h = E.hist[it.ultimaConclusao || chaveDia()];
  if(h){ h.tarefas=Math.max(0,h.tarefas-1); h.pontos=Math.max(0,h.pontos-pts); }
  it.ultimaConclusao = null;
  it.desfazer = null;
  salvar(true); emitir(EVENTOS.REDESENHAR);
}

/* Métricas do dia */
export function metricasDoDia(){
  let meta=0, feito=0;
  E.itens.forEach(it=>{
    if(it.status==="concluido" || it.freq!=="diaria") return;
    const m = it.tipo==="estudo" ? alvoEfetivo(it) : alvoEfetivo(it)*15; // tarefa vale 15min de esforço
    const f = it.tipo==="estudo" ? Math.min(it.feito||0, m) : Math.min((it.feito||0)*15, m);
    meta+=m; feito+=f;
  });
  return {meta, feito, pct: meta? Math.min(100, Math.round(feito/meta*100)) : 0};
}
