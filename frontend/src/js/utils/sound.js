/* Bip curto gerado pelo proprio navegador, sem arquivo de audio.
   Silencioso de proposito se o navegador bloquear o AudioContext. */

export function bip(freq,dur){
  try{
    const C = window.AudioContext||window.webkitAudioContext; if(!C) return;
    const ctx=new C(), o=ctx.createOscillator(), g=ctx.createGain();
    o.type="sine"; o.frequency.value=freq||880; o.connect(g); g.connect(ctx.destination);
    g.gain.setValueAtTime(.18,ctx.currentTime);
    g.gain.exponentialRampToValueAtTime(.001,ctx.currentTime+(dur||.5));
    o.start(); o.stop(ctx.currentTime+(dur||.5));
    setTimeout(()=>{ try{ ctx.close(); }catch(e){} }, ((dur||.5)*1000)+120);
  }catch(e){}
}

/* Modal — com devolução de foco e fechamento pelo Esc */
