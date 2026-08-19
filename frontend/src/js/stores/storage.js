/* Armazenamento com tres ambientes possiveis: nuvem do Claude,
   localStorage do navegador ou memoria da sessao. A escolha e
   feita uma vez, na carga, e o resto do app nao precisa saber
   qual esta em uso. */

export const Store = (function(){
  const mem = {};
  const temClaude = (typeof window !== "undefined") && window.storage && typeof window.storage.get === "function";
  let temLocal = false;
  try{ localStorage.setItem("__dl","1"); localStorage.removeItem("__dl"); temLocal = true; }catch(e){}
  const modo = temClaude ? "nuvem do Claude" : (temLocal ? "armazenamento do navegador" : "memória da sessão");
  return {
    modo,
    async ler(k){
      if(temClaude){ try{ const r = await window.storage.get(k); return r ? JSON.parse(r.value) : null; }catch(e){ return null; } }
      if(temLocal){ try{ const v = localStorage.getItem(k); return v ? JSON.parse(v) : null; }catch(e){ return null; } }
      return mem[k] !== undefined ? mem[k] : null;
    },
    async gravar(k,v){
      if(temClaude){ try{ await window.storage.set(k, JSON.stringify(v)); return true; }catch(e){ return false; } }
      if(temLocal){ try{ localStorage.setItem(k, JSON.stringify(v)); return true; }catch(e){ return false; } }
      mem[k]=v; return true;
    },
    async apagar(k){
      if(temClaude){ try{ await window.storage.delete(k); }catch(e){} return; }
      if(temLocal){ try{ localStorage.removeItem(k); }catch(e){} return; }
      delete mem[k];
    }
  };
})();
