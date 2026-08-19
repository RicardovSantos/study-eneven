"""Endpoints dos painéis e das recompensas."""

from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, status
from sqlalchemy import select

from app.api.deps import Sessao, UsuarioLogado, VinculoAtual
from app.core.exceptions import NaoEncontrado, SemPermissao
from app.models.enums import PapelFamiliar
from app.models.pontos import DesbloqueioRecompensa, NivelRecompensa, TrilhaRecompensa
from app.repositories import usuarios as repo
from app.schemas.dashboard import (
    CriarNivel,
    CriarTrilha,
    ItemHistorico,
    MetaDoDia,
    NivelPublico,
    PainelFamiliar,
    PainelPessoal,
    PremioPublico,
    ProgressoPublico,
    ResumoUsuario,
)
from app.services import dashboard as servico
from app.services import recompensas as servico_rec

router = APIRouter(tags=["painel"])


def _resumo(r) -> ResumoUsuario:
    return ResumoUsuario(**r.__dict__)


def _domingo_da(d: date) -> date:
    return d - timedelta(days=(d.weekday() + 1) % 7)


@router.get("/dashboard", response_model=PainelPessoal)
async def painel_pessoal(usuario: UsuarioLogado, vinculo: VinculoAtual, sessao: Sessao):
    hoje = date.today()
    domingo = _domingo_da(hoje)
    primeiro = hoje.replace(day=1)
    return PainelPessoal(
        resumo=_resumo(await servico.resumo_pessoal(sessao, usuario=usuario, hoje=hoje)),
        meta_do_dia=MetaDoDia(
            **await servico.objetivos_do_dia(sessao, usuario_id=usuario.id, hoje=hoje)
        ),
        serie_semana=await servico.minutos_por_dia(
            sessao, usuario_id=usuario.id, de=domingo, ate=domingo + timedelta(days=6)
        ),
        serie_mes=await servico.minutos_por_dia(
            sessao, usuario_id=usuario.id, de=primeiro, ate=hoje
        ),
    )


@router.get("/dashboard/familia", response_model=PainelFamiliar)
async def painel_familiar(usuario: UsuarioLogado, vinculo: VinculoAtual, sessao: Sessao):
    """Só o responsável enxerga o painel da família."""
    if vinculo.papel != PapelFamiliar.ADMIN:
        raise SemPermissao("Esta área é só do responsável da família.")
    hoje = date.today()
    return PainelFamiliar(
        eu=_resumo(await servico.resumo_pessoal(sessao, usuario=usuario, hoje=hoje)),
        dependentes=[
            _resumo(c)
            for c in await servico.resumo_da_familia(
                sessao, familia_id=vinculo.familia_id, hoje=hoje
            )
        ],
    )


@router.get("/historico", response_model=list[ItemHistorico])
async def historico(
    usuario: UsuarioLogado,
    vinculo: VinculoAtual,
    sessao: Sessao,
    limite: int = 10,
    deslocamento: int = 0,
    titular_id: UUID | None = None,
):
    alvo = usuario.id
    if titular_id is not None and titular_id != usuario.id:
        if vinculo.papel != PapelFamiliar.ADMIN:
            raise SemPermissao("Você só pode ver o próprio histórico.")
        if await repo.vinculo_na_familia(sessao, titular_id, vinculo.familia_id) is None:
            raise NaoEncontrado("Pessoa não encontrada nesta família.")
        alvo = titular_id

    itens = await servico.historico(
        sessao, usuario_id=alvo, limite=min(limite, 100), deslocamento=deslocamento
    )
    return [ItemHistorico(**i) for i in itens]


# ---------- recompensas ----------

async def _trilha_da_familia(sessao, trilha_id: UUID, vinculo) -> TrilhaRecompensa:
    t = await sessao.get(TrilhaRecompensa, trilha_id)
    if t is None or t.familia_id != vinculo.familia_id:
        raise NaoEncontrado("Trilha não encontrada.")
    if vinculo.papel == PapelFamiliar.DEPENDENTE and t.beneficiario_id != vinculo.usuario_id:
        raise NaoEncontrado("Trilha não encontrada.")
    return t


@router.post("/recompensas/trilhas", response_model=ProgressoPublico,
             status_code=status.HTTP_201_CREATED)
async def criar_trilha(dados: CriarTrilha, vinculo: VinculoAtual, sessao: Sessao):
    trilha = await servico_rec.criar_trilha(
        sessao, vinculo=vinculo,
        beneficiario_id=dados.beneficiario_id or vinculo.usuario_id,
        nome=dados.nome, escopo=dados.escopo, filtro=dados.filtro,
    )
    await sessao.commit()
    progresso = await servico_rec.avaliar(sessao, trilha=trilha)
    return _progresso(progresso)


def _progresso(p) -> ProgressoPublico:
    return ProgressoPublico(
        trilha_id=p.trilha.id,
        nome=p.trilha.nome,
        escopo=p.trilha.escopo,
        pontos=p.pontos,
        nivel_atual=NivelPublico.model_validate(p.nivel_atual) if p.nivel_atual else None,
        proximo_nivel=(
            NivelPublico.model_validate(p.proximo_nivel) if p.proximo_nivel else None
        ),
        faltam=p.faltam,
        percentual=p.percentual,
        niveis_desbloqueados=len(p.desbloqueados),
    )


@router.post("/recompensas/trilhas/{trilha_id}/niveis", response_model=NivelPublico,
             status_code=status.HTTP_201_CREATED)
async def adicionar_nivel(
    trilha_id: UUID, dados: CriarNivel, vinculo: VinculoAtual, sessao: Sessao
):
    trilha = await _trilha_da_familia(sessao, trilha_id, vinculo)
    nivel = await servico_rec.adicionar_nivel(
        sessao, trilha=trilha, vinculo=vinculo,
        pontos_necessarios=dados.pontos_necessarios, premio=dados.premio,
    )
    await sessao.commit()
    return NivelPublico.model_validate(nivel)


@router.get("/recompensas", response_model=list[ProgressoPublico])
async def minhas_trilhas(
    vinculo: VinculoAtual, sessao: Sessao, beneficiario_id: UUID | None = None
):
    """Avalia ao consultar: abrir a tela já desbloqueia o que foi alcançado."""
    alvo = vinculo.usuario_id
    if beneficiario_id is not None and beneficiario_id != vinculo.usuario_id:
        if vinculo.papel != PapelFamiliar.ADMIN:
            raise SemPermissao("Você só pode ver as próprias recompensas.")
        alvo = beneficiario_id

    trilhas = await servico_rec.trilhas_de(
        sessao, beneficiario_id=alvo, familia_id=vinculo.familia_id
    )
    saida = [_progresso(await servico_rec.avaliar(sessao, trilha=t)) for t in trilhas]
    await sessao.commit()
    return saida


@router.get("/recompensas/premios", response_model=list[PremioPublico])
async def meus_premios(vinculo: VinculoAtual, sessao: Sessao):
    r = await sessao.execute(
        select(DesbloqueioRecompensa)
        .join(NivelRecompensa, NivelRecompensa.id == DesbloqueioRecompensa.nivel_id)
        .join(TrilhaRecompensa, TrilhaRecompensa.id == NivelRecompensa.trilha_id)
        .where(
            DesbloqueioRecompensa.beneficiario_id == vinculo.usuario_id,
            TrilhaRecompensa.familia_id == vinculo.familia_id,
        )
        .order_by(DesbloqueioRecompensa.desbloqueado_em.desc())
    )
    return [PremioPublico.model_validate(d) for d in r.scalars()]


@router.post("/recompensas/premios/{premio_id}/solicitar", response_model=PremioPublico)
async def solicitar_premio(premio_id: UUID, vinculo: VinculoAtual, sessao: Sessao):
    d = await servico_rec.solicitar(
        sessao, desbloqueio_id=premio_id, usuario_id=vinculo.usuario_id
    )
    await sessao.commit()
    return PremioPublico.model_validate(d)


@router.post("/recompensas/premios/{premio_id}/entregar", response_model=PremioPublico)
async def confirmar_entrega(premio_id: UUID, vinculo: VinculoAtual, sessao: Sessao):
    d = await servico_rec.confirmar_entrega(
        sessao, desbloqueio_id=premio_id, vinculo=vinculo
    )
    await sessao.commit()
    return PremioPublico.model_validate(d)
