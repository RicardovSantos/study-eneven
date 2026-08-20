/* Card "Matérias" na tela Objetivos: lista, cria, renomeia e arquiva.

   Só é chamado em modo servidor (ver pages/index.js) — sem servidor o
   campo "Curso/Certificação" do formulário continua sendo texto livre,
   como sempre foi, e este card nem existe (fica com o
   `style="display:none"` estático do index.html). */

import { $ } from "../utils/dom.js";
import { E } from "../stores/app-store.js";
import { esc } from "../utils/format.js";

export function renderMaterias(){
  $("#card-materias").style.display = "";

  const materias = E.materias || [];
  $("#lista-materias").innerHTML = materias.length
    ? materias.map(m => (
        '<div class="item">'+
          '<div class="info"><div class="nome">'+esc(m.nome)+'</div></div>'+
          '<button class="icone-btn del" type="button" data-del-materia="'+m.id+'" aria-label="Arquivar '+esc(m.nome)+'">🗑</button>'+
          '<button class="icone-btn edit" type="button" data-edit-materia="'+m.id+'" aria-label="Renomear '+esc(m.nome)+'">✎</button>'+
        '</div>'
      )).join("")
    : '<p class="vazio">Nenhuma matéria cadastrada ainda.</p>';

  popularSelectMateria();
}

/* Preenche o <select> do formulário de objetivo com as matérias da
   família, preservando a seleção atual quando possível. */
export function popularSelectMateria(){
  const sel = $("#f-cat");
  const atual = sel.value;
  const materias = E.materias || [];
  sel.innerHTML = '<option value="">Sem matéria</option>'+
    materias.map(m => '<option value="'+m.id+'">'+esc(m.nome)+'</option>').join("");
  if(atual && materias.some(m => m.id === atual)) sel.value = atual;
}
