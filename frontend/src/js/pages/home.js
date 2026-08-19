/* Tela Home: painel pessoal com meta do dia, graficos da semana e do
   mes, placar e historico mensal agregado. So le o estado e desenha. */

import { $ } from "../utils/dom.js";
import { E } from "../stores/app-store.js";
import { hoje, chaveDia, domingoDa, p2 } from "../utils/dates.js";
import { fmtHM } from "../utils/format.js";
import { fotoOu } from "../utils/avatar.js";
import { metricasDoDia } from "../services/objetivos.js";
import { graficoBarras, graficoLinha } from "../components/charts.js";

export function renderHome(){
  if(!E.logado) return;
  const u=E.usuario||{};
  $("#home-foto").src = fotoOu(u);
  $("#home-nome").textContent = u.nome || "Sem nome";

  const d = metricasDoDia();
  $("#dia-barra").style.width = d.pct+"%";
  $("#dia-txt").textContent = d.pct+"%";
  $("#dia-detalhe").textContent = d.meta
    ? fmtHM(d.feito)+" de "+fmtHM(d.meta)+" planejados para hoje"
    : "Sem objetivos diários. Cadastre um na aba Objetivos.";

  // Semana
  const dom = domingoDa(hoje()), rot=["dom","seg","ter","qua","qui","sex","sáb"], vals=[];
  for(let i=0;i<7;i++){ const dt=new Date(dom); dt.setDate(dom.getDate()+i);
    vals.push(Math.round((E.hist[chaveDia(dt)]||{}).min||0)); }
  graficoBarras($("#g-semana"), vals, rot);
  const totalSem = vals.reduce((a,b)=>a+b,0);
  $("#semana-detalhe").textContent = totalSem
    ? fmtHM(totalSem)+" de estudo nesta semana · média "+fmtHM(totalSem/7)+"/dia"
    : "Nenhum tempo registrado nesta semana ainda.";

  // Mensal
  const ag=hoje(), dias=new Date(ag.getFullYear(),ag.getMonth()+1,0).getDate();
  const vm=[], rm=[];
  for(let i=1;i<=dias;i++){ const dt=new Date(ag.getFullYear(),ag.getMonth(),i);
    vm.push(Math.round((E.hist[chaveDia(dt)]||{}).min||0)); rm.push(p2(i)); }
  graficoLinha($("#g-mensal"), vm, rm);
  const totalMes = vm.reduce((a,b)=>a+b,0);
  const ativos = vm.filter(v=>v>0).length;
  $("#mensal-detalhe").textContent = totalMes
    ? fmtHM(totalMes)+" no mês · "+ativos+" dia(s) com estudo"
    : "O gráfico se preenche conforme você usa o cronômetro.";


  $("#pl-concl").textContent = E.concluidos;
  $("#pl-pontos").textContent = E.pontos;

  // Histórico mensal
  const meses={};
  Object.keys(E.hist).forEach(k=>{
    const m=k.slice(0,7), h=E.hist[k];
    const a = meses[m] || (meses[m]={min:0,tarefas:0,pontos:0});
    a.min+=h.min; a.tarefas+=h.tarefas; a.pontos+=h.pontos;
  });
  const nomes=["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"];
  const linhas = Object.keys(meses).sort().reverse().slice(0,12).map(m=>{
    const a=meses[m], partes=m.split("-"), ano=partes[0], mm=partes[1];
    return "<tr><td>"+nomes[+mm-1]+"/"+ano.slice(2)+"</td><td>"+fmtHM(a.min)+
      "</td><td>"+a.tarefas+"</td><td>"+a.pontos+"</td></tr>";
  }).join("");
  $("#tb-hist").innerHTML = linhas || '<tr><td colspan="4" class="vazio">Ainda sem histórico.</td></tr>';
}
