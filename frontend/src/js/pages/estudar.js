/* Tela Estudar: execucao do que foi cadastrado.

   Nao cria nem edita objetivos — so mostra o que cabe no periodo
   atual, separado por frequencia, e oferece iniciar o cronometro ou
   marcar como concluido. */

import { $ } from "../utils/dom.js";
import { E } from "../stores/app-store.js";
import { esc, fmtHM, fmtRelogio } from "../utils/format.js";
import { alvoEfetivo, restante, metricasDoDia } from "../services/objetivos.js";

export function linhaObjetivo(it){
  const conc = restante(it)<=0;
  const acEx = (it.saldo||0)>0;
  const tags = '<span class="tag cat">'+esc(it.cat)+'</span>'+
    (acEx? '<span class="tag acum">+'+(it.tipo==="estudo"?fmtHM(it.saldo):it.saldo+"x")+' acumulado</span>':"")+
    (it.acum?"":'<span class="tag fixo">fixo</span>');
  if(it.tipo==="estudo"){
    const total = alvoEfetivo(it), falta = restante(it);
    // ordem do protótipo: nome · ▶ · relógio · ✓
    return '<div class="item">'+
      '<div class="info"><div class="nome">'+esc(it.nome)+'</div>'+
      '<div class="sub">'+tags+'<span>meta '+fmtHM(total)+'</span></div></div>'+
      (conc
        ? '<span class="relogio pronto">00:00:00</span>'+
          '<button class="marcador on" type="button" data-check="'+it.id+'" aria-label="Reabrir '+esc(it.nome)+'">✓</button>'
        : '<button class="icone-btn play" type="button" data-play="'+it.id+'" aria-label="Iniciar '+esc(it.nome)+'">▶</button>'+
          '<span class="relogio">'+fmtRelogio(falta*60)+'</span>'+
          '<button class="marcador" type="button" data-check="'+it.id+'" aria-label="Concluir '+esc(it.nome)+'">✓</button>')+
      '</div>';
  }
  // tarefa: nome · contagem · caixa azul (protótipo "Tarefas mensal")
  const feitas = Math.min(it.feito||0, alvoEfetivo(it));
  return '<div class="item">'+
    '<div class="info"><div class="nome">'+esc(it.nome)+'</div>'+
    '<div class="sub">'+tags+'<span>'+feitas+" de "+alvoEfetivo(it)+'</span></div></div>'+
    '<button class="icone-btn edit" type="button" data-mais="'+it.id+'" aria-label="Marcar uma de '+esc(it.nome)+'">＋</button>'+
    '<span class="qtd">'+alvoEfetivo(it)+'</span>'+
    '<button class="caixa'+(conc?" on":"")+'" type="button" data-check="'+it.id+'" aria-pressed="'+conc+
      '" aria-label="Concluir '+esc(it.nome)+'">✓</button>'+
    '</div>';
}
export function renderObjetivos(){
  const ativos = E.itens.filter(it=>it.status!=="concluido");
  const porFreq = f => ativos.filter(it=>it.freq===f);
  const pinta = (sel,f,txt)=>{
    const l=porFreq(f);
    $(sel).innerHTML = l.length ? l.map(linhaObjetivo).join("") : '<p class="vazio">'+txt+"</p>";
  };
  pinta("#lista-diaria","diaria","Nenhuma tarefa diária cadastrada.");
  pinta("#lista-semanal","semanal","Nenhuma tarefa semanal cadastrada.");
  pinta("#lista-mensal","mensal","Nenhuma tarefa mensal cadastrada.");

  const feitos = E.itens.filter(it=>it.status==="concluido");
  $("#lista-feitos").innerHTML = feitos.length ? feitos.map(it=>
    '<div class="item"><div class="info"><div class="nome">'+esc(it.nome)+'</div>'+
    '<div class="sub"><span class="tag ok">meta batida</span><span>'+
    (it.tipo==="estudo"? fmtHM(it.progresso||0) : (it.progresso||0)+"x")+' no total</span></div></div>'+
    '<button class="icone-btn edit" type="button" data-reabrir="'+it.id+'" aria-label="Reabrir '+esc(it.nome)+'">↺</button></div>'
  ).join("") : '<p class="vazio">Nenhum objetivo finalizado ainda. Ele aparece aqui quando o total da meta for atingido.</p>';

  const d=metricasDoDia();
  const pend = ativos.filter(it=>it.freq==="diaria" && restante(it)>0).length;
  $("#hoje-resumo").innerHTML = d.meta
    ? "<b>"+d.pct+"%</b> do dia concluído · "+pend+" objetivo(s) diário(s) em aberto<br>"+
      fmtHM(Math.max(0,d.meta-d.feito))+" ainda planejados para hoje"
    : "Sem plano para hoje. Cadastre objetivos na aba Objetivos.";
}
