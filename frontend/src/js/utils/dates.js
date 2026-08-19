/* Chaves de data usadas para agrupar historico e periodos.

   O formato "AAAA-MM-DD" e montado na mao, e nao com toISOString(),
   porque toISOString converte para UTC: perto da meia-noite isso
   jogaria o registro para o dia errado no fuso do Brasil. */

export const p2 = n => String(n).padStart(2,"0");
export const hoje = () => new Date();

export function chaveDia(d){ d=d||hoje(); return d.getFullYear()+"-"+p2(d.getMonth()+1)+"-"+p2(d.getDate()); }
export function chaveMes(d){ d=d||hoje(); return d.getFullYear()+"-"+p2(d.getMonth()+1); }
export function domingoDa(d){ const x=new Date(d.getFullYear(),d.getMonth(),d.getDate()); x.setDate(x.getDate()-x.getDay()); return x; }
export function chaveSemana(d){ return "S"+chaveDia(domingoDa(d||hoje())); }
export function chavePeriodo(freq,d){ return freq==="diaria"?chaveDia(d) : freq==="semanal"?chaveSemana(d) : chaveMes(d); }
