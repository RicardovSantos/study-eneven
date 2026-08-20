/* Adaptador entre o formato da API e o formato local que as telas
   (pages/objetivos.js, pages/estudar.js, pages/home.js) já sabem
   desenhar.

   Por que um adaptador em vez de reescrever as telas: renderCrud(),
   linhaObjetivo() e renderHome() já leem E.itens/E.hist/E.pontos num
   formato específico, testado e funcionando. Popular esse mesmo
   formato a partir da API reaproveita esse código inteiro sem risco de
   regressão — só a origem do dado muda.

   Ponto de atenção: a tela Objetivos (CRUD) e a tela Estudar (execução)
   precisam de *ids diferentes* no mesmo campo it.id — a primeira precisa
   do id do objetivo (para editar/excluir), a segunda precisa do id da
   ocorrência (para concluir/tocar o cronômetro). Por isso E.itens é
   populado de novo, com o formato certo, toda vez que a tela muda — ver
   pages/index.js. As duas formas nunca coexistem ao mesmo tempo. */

import { E } from "../stores/app-store.js";
import * as objetivosApi from "../api/objetivos.js";
import * as materiasApi from "../api/materias.js";
import * as painelApi from "../api/painel.js";

const FREQ_API_PARA_LOCAL = { daily: "diaria", weekly: "semanal", monthly: "mensal", custom: "diaria" };
const FREQ_LOCAL_PARA_API = { diaria: "daily", semanal: "weekly", mensal: "monthly" };
const TIPO_API_PARA_LOCAL = { study: "estudo", task: "tarefa" };
const TIPO_LOCAL_PARA_API = { estudo: "study", tarefa: "task" };
const STATUS_API_PARA_LOCAL = {
  in_progress: "andamento", completed: "concluido", paused: "pausado", archived: "arquivado",
};

/* Objetivo sem matéria (ou matéria arquivada, que some de E.materias mas
   fica na memória de um objetivo antigo) cai nesta categoria neutra em
   vez de um campo vazio, que ficaria com cara de bug. */
const SEM_MATERIA = "Sem matéria";

function nomeMateria(materiaId){
  if(!materiaId) return SEM_MATERIA;
  const m = (E.materias || []).find(x => x.id === materiaId);
  return m ? m.nome : SEM_MATERIA;
}

/* Popula E.materias no formato que pages/materias.js lê. Buscada junto
   das duas telas que mostram objetivo (Objetivos e Estudar), porque as
   duas precisam traduzir materia_id em nome — ver nomeMateria() acima. */
export async function sincronizarMaterias(){
  E.materias = await materiasApi.listar();
}

function itemCrud(objetivo){
  const tipo = TIPO_API_PARA_LOCAL[objetivo.tipo] || "estudo";
  const emHoras = tipo === "estudo";
  return {
    id: objetivo.id,
    tipo, nome: objetivo.nome, cat: nomeMateria(objetivo.materia_id),
    materiaId: objetivo.materia_id || null,
    freq: FREQ_API_PARA_LOCAL[objetivo.frequencia] || "diaria",
    qtd: emHoras ? Math.round((objetivo.meta_periodo / 60) * 10) / 10 : objetivo.meta_periodo,
    uni: emHoras ? "horas" : "vezes",
    alvo: objetivo.meta_periodo,
    totalMeta: objetivo.meta_total || 0,
    acum: !!objetivo.acumula_pendencia,
    permiteAdiantar: !!objetivo.permite_adiantar,
    maxAdiantamentos: objetivo.max_adiantamentos ?? 1,
    status: STATUS_API_PARA_LOCAL[objetivo.status] || "andamento",
    feito: 0, saldo: 0, progresso: 0,
  };
}

function itemEstudar(objetivo, ocorrencia){
  const tipo = TIPO_API_PARA_LOCAL[objetivo.tipo] || "estudo";
  return {
    id: ocorrencia.id,             // de propósito: id da OCORRÊNCIA, não do objetivo
    ocorrenciaId: ocorrencia.id,
    objetivoId: objetivo.id,
    tipo, nome: objetivo.nome, cat: nomeMateria(objetivo.materia_id),
    freq: FREQ_API_PARA_LOCAL[objetivo.frequencia] || "diaria",
    acum: !!objetivo.acumula_pendencia,
    alvo: ocorrencia.meta,
    saldo: 0,                       // acúmulo não é exposto pela API ainda
    feito: ocorrencia.realizado,
    progresso: ocorrencia.realizado,
    totalMeta: objetivo.meta_total || 0,
    status: ocorrencia.status === "completed" ? "concluido" : "andamento",
  };
}

/* Popula E.itens no formato que renderCrud() espera. */
export async function sincronizarObjetivosCrud(){
  const [, lista] = await Promise.all([sincronizarMaterias(), objetivosApi.listar()]);
  E.itens = lista.map(itemCrud);
}

/* Popula E.itens no formato que linhaObjetivo()/renderObjetivos() (tela
   Estudar) esperam — com o id trocado para o da ocorrência.

   A API materializa a agenda dias à frente (JANELA_PADRAO_DIAS no
   backend), então um objetivo diário chega com uma ocorrência por dia.
   A tela local sempre mostrou uma linha por objetivo — o período atual,
   não a fila inteira — então aqui fica só a ocorrência "da vez" de cada
   objetivo: a pendente mais próxima, ou a mais recente já concluída se
   não houver nenhuma pendente na janela buscada. */
export async function sincronizarOcorrenciasEstudar(){
  const ate = new Date();
  ate.setDate(ate.getDate() + 31);          // cobre um ciclo mensal inteiro
  const [, objetivos, ocorrencias] = await Promise.all([
    sincronizarMaterias(),
    objetivosApi.listar(),
    objetivosApi.ocorrencias({ ate: ate.toISOString().slice(0, 10) }),
  ]);

  const porObjetivo = new Map();
  for(const oc of ocorrencias){
    const atual = porObjetivo.get(oc.objetivo_id);
    if(!atual){ porObjetivo.set(oc.objetivo_id, oc); continue; }
    const pendenteNova = oc.status === "pending";
    const pendenteAtual = atual.status === "pending";
    const troca = (pendenteNova && !pendenteAtual)
      || (pendenteNova === pendenteAtual && oc.prevista_para < atual.prevista_para);
    if(troca) porObjetivo.set(oc.objetivo_id, oc);
  }

  const porId = new Map(objetivos.map((o) => [o.id, o]));
  E.itens = [...porObjetivo.entries()]
    .filter(([objetivoId]) => porId.has(objetivoId))
    .map(([objetivoId, oc]) => itemEstudar(porId.get(objetivoId), oc));
}

/* Popula E.familiaDependentes com o resumo de cada dependente, no
   formato que pages/familia.js já lê. Só chamada quando E.papel é
   "admin" — a API 403a a pessoa dependente aqui (ver router.js). */
export async function sincronizarFamilia(){
  const d = await painelApi.familia();
  E.familiaDependentes = d.dependentes;
}

/* Popula E.trilhas/E.premiosLista com o progresso e os prêmios de
   E.recompensasBeneficiario (por padrão, a própria pessoa logada).
   Responsável pode trocar de beneficiário (ver pages/recompensas.js);
   dependente só tem a si mesmo.

   As duas buscas não podem ser paralelas: só GET /recompensas roda o
   avaliar() que desbloqueia nível (soma pontos e grava o desbloqueio);
   GET /recompensas/premios só lista o que já foi desbloqueado. Buscar
   os prêmios ao mesmo tempo arriscaria ler a lista antes do desbloqueio
   mais recente ser gravado. */
export async function sincronizarRecompensas(){
  if(!E.recompensasBeneficiario){
    E.recompensasBeneficiario = { id: E.usuario.id, nome: "Eu mesmo" };
  }
  if(E.papel === "admin" && !E.familiaDependentes) await sincronizarFamilia();

  const alvo = E.recompensasBeneficiario.id;
  const ehEu = alvo === E.usuario.id;
  E.trilhas = await painelApi.recompensas(ehEu ? undefined : alvo);
  E.premiosLista = await painelApi.premios(ehEu ? undefined : alvo);
}

/* Popula E.pontos/E.concluidos/E.hist a partir do painel, no formato
   que renderHome() e metricasDoDia() já leem. */
export async function sincronizarPainelHome(){
  const d = await painelApi.pessoal();
  E.pontos = d.resumo.pontos_totais;
  E.concluidos = d.resumo.concluidas_total;
  E.hist = {};
  for(const [dia, min] of Object.entries({ ...d.serie_semana, ...d.serie_mes })){
    E.hist[dia] = { min, tarefas: 0, pontos: 0 };
  }
  return d;
}

const TAMANHO_PAGINA_HISTORICO = 10;

/* Popula E.historico com os últimos lançamentos de pontos, paginados.
   Chamado sem argumento ao abrir a Home (reinicia do zero); chamado
   com continuar:true pelo botão "Carregar mais" (acrescenta a
   próxima página em vez de substituir). */
export async function sincronizarProgresso({ continuar = false } = {}){
  if(!continuar){ E.historico = []; E.historicoDeslocamento = 0; E.historicoTemMais = true; }
  const pagina = await painelApi.historico({
    limite: TAMANHO_PAGINA_HISTORICO, deslocamento: E.historicoDeslocamento || 0,
  });
  E.historico = [...(E.historico || []), ...pagina];
  E.historicoDeslocamento = (E.historicoDeslocamento || 0) + pagina.length;
  E.historicoTemMais = pagina.length === TAMANHO_PAGINA_HISTORICO;
}

/* Traduz os campos do formulário (já lidos por pages/objetivos.js no
   formato local) para o contrato da API. */
export function paraApiObjetivo({
  tipo, nome, freq, alvo, totalMeta, acum, status, materiaId,
  permiteAdiantar, maxAdiantamentos,
}){
  const dados = {
    tipo: TIPO_LOCAL_PARA_API[tipo] || "study",
    nome,
    materia_id: materiaId || null,
    meta_periodo: alvo,
    meta_total: totalMeta > 0 ? totalMeta : null,
    frequencia: FREQ_LOCAL_PARA_API[freq] || "daily",
    acumula_pendencia: acum,
    permite_adiantar: !!permiteAdiantar,
    max_adiantamentos: maxAdiantamentos ?? 1,
  };
  // Tarefa sem cronômetro precisa de pontuação fixa (o banco exige).
  // O formulário ainda não tem esse campo — ver docs/o-que-falta.md.
  if(dados.tipo === "task") dados.pontos_fixos = 5;
  if(status === "concluido") dados.status = "completed";
  return dados;
}
