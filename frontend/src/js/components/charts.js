/* Graficos em SVG puro, sem biblioteca.

   Sao 40 linhas e cobrem os dois casos que o app tem (barras da
   semana e linha do mes). Trocar por Chart.js so acrescentaria
   ~200 KB de dependencia para o mesmo resultado. */

import { esc, fmtHM } from "../utils/format.js";

export function graficoBarras(alvoEl, valores, rotulos){
  const L=300,A=130,pe=26,pd=10,pt=12,pb=20;
  const max = Math.max(60, ...valores);
  const lg = (L-pe-pd)/valores.length;
  let s = '<svg class="grafico" viewBox="0 0 '+L+' '+A+'" role="img" aria-label="Minutos de estudo por dia da semana">';
  [0,.5,1].forEach(f=>{
    const y = pt+(A-pt-pb)*f;
    s += '<line x1="'+pe+'" y1="'+y+'" x2="'+(L-pd)+'" y2="'+y+'" stroke="#D9D8EC" stroke-width="1"/>';
    s += '<text x="'+(pe-4)+'" y="'+(y+3.5)+'" font-size="8" fill="#6B6B85" text-anchor="end">'+Math.round(max*(1-f))+'</text>';
  });
  valores.forEach((v,i)=>{
    const h = max? (A-pt-pb)*(v/max) : 0;
    const x = pe + i*lg + lg*.22, w = lg*.56, y = A-pb-h;
    s += '<rect x="'+x.toFixed(1)+'" y="'+y.toFixed(1)+'" width="'+w.toFixed(1)+'" height="'+Math.max(0,h).toFixed(1)+
         '" rx="3" fill="#7C6FD6"><title>'+esc(rotulos[i])+": "+fmtHM(v)+'</title></rect>';
    s += '<text x="'+(x+w/2).toFixed(1)+'" y="'+(A-6)+'" font-size="9" fill="#6B6B85" text-anchor="middle">'+esc(rotulos[i])+'</text>';
  });
  s += '</svg>';
  alvoEl.innerHTML = s;
}
export function graficoLinha(alvoEl, valores, rotulos){
  const L=300,A=120,pe=26,pd=10,pt=12,pb=18;
  const max = Math.max(60, ...valores);
  const n = valores.length;
  const px = i => pe + (L-pe-pd)*(n>1? i/(n-1):0);
  const py = v => pt + (A-pt-pb)*(1 - (max? v/max:0));
  let s = '<svg class="grafico" viewBox="0 0 '+L+' '+A+'" role="img" aria-label="Evolução do estudo no mês">';
  [0,.5,1].forEach(f=>{
    const y = pt+(A-pt-pb)*f;
    s += '<line x1="'+pe+'" y1="'+y+'" x2="'+(L-pd)+'" y2="'+y+'" stroke="#D9D8EC" stroke-width="1"/>';
    s += '<text x="'+(pe-4)+'" y="'+(y+3.5)+'" font-size="8" fill="#6B6B85" text-anchor="end">'+Math.round(max*(1-f))+'</text>';
  });
  const pts = valores.map((v,i)=>px(i).toFixed(1)+","+py(v).toFixed(1));
  s += '<polygon points="'+pe+','+(A-pb)+' '+pts.join(" ")+' '+(L-pd)+','+(A-pb)+'" fill="#9B3FE0" opacity=".10"/>';
  s += '<polyline points="'+pts.join(" ")+'" fill="none" stroke="#9B3FE0" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>';
  valores.forEach((v,i)=>{ if(v>0) s+='<circle cx="'+px(i).toFixed(1)+'" cy="'+py(v).toFixed(1)+'" r="2.4" fill="#9B3FE0"><title>'+esc(rotulos[i])+": "+fmtHM(v)+'</title></circle>'; });
  const marcos=[0,Math.floor(n/2),n-1];
  marcos.forEach(i=>{ s+='<text x="'+px(i).toFixed(1)+'" y="'+(A-4)+'" font-size="8" fill="#6B6B85" text-anchor="middle">'+esc(rotulos[i])+'</text>'; });
  s += '</svg>';
  alvoEl.innerHTML = s;
}
