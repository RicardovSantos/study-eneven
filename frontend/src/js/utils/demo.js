/* Dados de exemplo: 7 objetivos e 45 dias de historico, para dar o
   que ver nos graficos sem esperar semanas de uso real. */

import { E, salvar } from "../stores/app-store.js";
import { hoje, chaveDia, chavePeriodo } from "./dates.js";
import { id } from "./format.js";
import { modal } from "../components/modal.js";
import { ir } from "../router.js";
import { emitir, EVENTOS } from "../core/bus.js";

export function carregarDemo(){
  const mk=(tipo,nome,cat,freq,alvo,acum,totalMeta)=>({
    id:id(),tipo,nome,cat,freq,qtd:tipo==="estudo"?alvo/60:alvo,uni:tipo==="estudo"?"horas":"vezes",
    alvo,totalMeta,acum,status:"andamento",feito:0,saldo:0,progresso:0,
    periodoRef:chavePeriodo(freq,hoje()),criadoEm:chaveDia(),ultimaConclusao:null});
  E.itens = [
    mk("estudo","Curso Inglês","Idioma","diaria",60,true,360*60),
    mk("estudo","Faculdade EAD","Faculdade","diaria",120,true,800*60),
    mk("estudo","Curso AWS","Certificação","diaria",60,false,120*60),
    mk("estudo","Projeto Portfólio","Projeto","semanal",300,true,200*60),
    mk("tarefa","Entrevistas","Outro","mensal",5,false,60),
    mk("tarefa","Projeto GitHub","Projeto","mensal",3,true,36),
    mk("tarefa","Conexões LinkedIn","Outro","mensal",4,true,48)
  ];
  E.itens[0].saldo=60; E.itens[1].feito=45;
  E.hist={}; E.pontos=0; E.concluidos=0;
  for(let i=44;i>=0;i--){
    const d=new Date(); d.setDate(d.getDate()-i);
    const fds=[0,6].includes(d.getDay());
    const base=fds? 40:130;
    const min=Math.max(0, Math.round(base + Math.sin(i/3)*45 + (Math.random()*60-25)));
    if(min<15 && Math.random()<.4) continue;
    const tarefas=Math.random()<.55?1:0;
    const pontos=Math.round(min/6)+tarefas*8+(min>0?10:0);
    E.hist[chaveDia(d)]={min,tarefas,pontos};
    E.pontos+=pontos; E.concluidos+= (min>0?1:0)+tarefas;
  }
  salvar(true); emitir(EVENTOS.REDESENHAR);
  modal({selo:"ok",icone:"✓",titulo:"Exemplo carregado",
    texto:"7 objetivos e 45 dias de histórico foram criados para você testar os gráficos.",
    botoes:[{r:"Ver o painel",c:"btn-verde",f:()=>ir("home")},{r:"OK",c:"btn-cinza"}]});
}
