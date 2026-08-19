"""Trilhas de recompensa, níveis e desbloqueio.

Uma trilha soma pontos de um recorte — tudo, uma matéria, um objetivo ou
um conjunto — e tem níveis com prêmios. Ao alcançar o limite de um nível,
ele desbloqueia.

**Desbloquear não desconta pontos.** O total é acumulativo, então os
níveis seguintes continuam alcançáveis (seção 10.2). Isso é diferente de
uma loja de recompensas, onde o ponto é moeda e some ao gastar — a
especificação trata a loja como evolução futura, não como o MVP.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import JaExiste, NaoEncontrado, SemPermissao
from app.models.enums import EscopoTrilha, PapelFamiliar, StatusRecompensa
from app.models.identidade import MembroFamilia
from app.models.pontos import (
    DesbloqueioRecompensa,
    LancamentoPontos,
    NivelRecompensa,
    TrilhaRecompensa,
)
from app.repositories import usuarios as repo_usuarios


@dataclass
class ProgressoTrilha:
    trilha: TrilhaRecompensa
    pontos: int
    nivel_atual: NivelRecompensa | None
    proximo_nivel: NivelRecompensa | None
    faltam: int
    percentual: int
    desbloqueados: list[UUID]


async def pontos_da_trilha(
    sessao: AsyncSession, trilha: TrilhaRecompensa
) -> int:
    """Soma o recorte que a trilha define."""
    consulta = select(func.coalesce(func.sum(LancamentoPontos.pontos), 0)).where(
        LancamentoPontos.beneficiario_id == trilha.beneficiario_id
    )
    filtro = trilha.filtro or {}

    if trilha.escopo == EscopoTrilha.MATERIA and filtro.get("materia_id"):
        consulta = consulta.where(
            LancamentoPontos.materia_id == UUID(str(filtro["materia_id"]))
        )
    elif trilha.escopo == EscopoTrilha.OBJETIVO and filtro.get("objetivo_id"):
        consulta = consulta.where(
            LancamentoPontos.objetivo_id == UUID(str(filtro["objetivo_id"]))
        )
    elif trilha.escopo == EscopoTrilha.CONJUNTO and filtro.get("objetivos"):
        ids = [UUID(str(x)) for x in filtro["objetivos"]]
        consulta = consulta.where(LancamentoPontos.objetivo_id.in_(ids))

    r = await sessao.execute(consulta)
    return int(r.scalar_one() or 0)


async def criar_trilha(
    sessao: AsyncSession,
    *,
    vinculo: MembroFamilia,
    beneficiario_id: UUID,
    nome: str,
    escopo: EscopoTrilha,
    filtro: dict | None = None,
) -> TrilhaRecompensa:
    """Responsável cria trilha para si ou para um dependente da família."""
    if vinculo.papel != PapelFamiliar.ADMIN:
        raise SemPermissao("Apenas o responsável configura recompensas.")
    if beneficiario_id != vinculo.usuario_id:
        alvo = await repo_usuarios.vinculo_na_familia(
            sessao, beneficiario_id, vinculo.familia_id
        )
        if alvo is None:
            raise SemPermissao("Esta pessoa não faz parte da sua família.")

    trilha = TrilhaRecompensa(
        beneficiario_id=beneficiario_id,
        familia_id=vinculo.familia_id,
        criador_id=vinculo.usuario_id,
        nome=nome,
        escopo=escopo,
        filtro=filtro,
    )
    sessao.add(trilha)
    await sessao.flush()
    return trilha


async def adicionar_nivel(
    sessao: AsyncSession,
    *,
    trilha: TrilhaRecompensa,
    vinculo: MembroFamilia,
    pontos_necessarios: int,
    premio: str,
) -> NivelRecompensa:
    """Numera sozinho e exige limites crescentes.

    Um nível 3 que custa menos que o 2 tornaria a escada sem sentido: o
    usuário desbloquearia fora de ordem.
    """
    if vinculo.papel != PapelFamiliar.ADMIN:
        raise SemPermissao("Apenas o responsável configura recompensas.")

    r = await sessao.execute(
        select(
            func.coalesce(func.max(NivelRecompensa.numero), 0),
            func.coalesce(func.max(NivelRecompensa.pontos_necessarios), 0),
        ).where(NivelRecompensa.trilha_id == trilha.id)
    )
    ultimo_numero, maior_limite = r.one()

    if pontos_necessarios <= int(maior_limite or 0):
        raise JaExiste(
            f"O nível anterior exige {maior_limite} pontos; "
            f"este precisa exigir mais do que isso."
        )

    nivel = NivelRecompensa(
        trilha_id=trilha.id,
        numero=int(ultimo_numero or 0) + 1,
        pontos_necessarios=pontos_necessarios,
        premio=premio,
    )
    sessao.add(nivel)
    await sessao.flush()
    return nivel


async def avaliar(
    sessao: AsyncSession, *, trilha: TrilhaRecompensa, agora: datetime | None = None
) -> ProgressoTrilha:
    """Calcula o progresso e desbloqueia o que foi alcançado.

    Idempotente: a restrição única (nível, beneficiário) impede
    desbloquear o mesmo prêmio duas vezes, mesmo com chamadas
    simultâneas.
    """
    agora = agora or datetime.now(UTC)
    pontos = await pontos_da_trilha(sessao, trilha)

    r = await sessao.execute(
        select(NivelRecompensa)
        .where(NivelRecompensa.trilha_id == trilha.id, NivelRecompensa.ativo.is_(True))
        .order_by(NivelRecompensa.pontos_necessarios)
    )
    niveis = list(r.scalars())

    ja = await sessao.execute(
        select(DesbloqueioRecompensa.nivel_id).where(
            DesbloqueioRecompensa.beneficiario_id == trilha.beneficiario_id,
            DesbloqueioRecompensa.nivel_id.in_([n.id for n in niveis]) if niveis else False,
        )
    )
    desbloqueados = {x for (x,) in ja}

    novos = []
    for nivel in niveis:
        if pontos >= nivel.pontos_necessarios and nivel.id not in desbloqueados:
            novos.append(
                DesbloqueioRecompensa(
                    nivel_id=nivel.id,
                    beneficiario_id=trilha.beneficiario_id,
                    status=StatusRecompensa.DESBLOQUEADA,
                    desbloqueado_em=agora,
                )
            )
            desbloqueados.add(nivel.id)
    if novos:
        sessao.add_all(novos)
        await sessao.flush()

    alcancados = [n for n in niveis if pontos >= n.pontos_necessarios]
    pendentes = [n for n in niveis if pontos < n.pontos_necessarios]
    atual = alcancados[-1] if alcancados else None
    proximo = pendentes[0] if pendentes else None

    if proximo is None:
        faltam, percentual = 0, 100
    else:
        base = atual.pontos_necessarios if atual else 0
        faltam = proximo.pontos_necessarios - pontos
        vao = proximo.pontos_necessarios - base
        percentual = min(100, max(0, round((pontos - base) / vao * 100))) if vao else 0

    return ProgressoTrilha(
        trilha=trilha,
        pontos=pontos,
        nivel_atual=atual,
        proximo_nivel=proximo,
        faltam=faltam,
        percentual=percentual,
        desbloqueados=sorted(desbloqueados, key=str),
    )


async def trilhas_de(
    sessao: AsyncSession, *, beneficiario_id: UUID, familia_id: UUID
) -> list[TrilhaRecompensa]:
    r = await sessao.execute(
        select(TrilhaRecompensa).where(
            TrilhaRecompensa.beneficiario_id == beneficiario_id,
            TrilhaRecompensa.familia_id == familia_id,
            TrilhaRecompensa.ativo.is_(True),
        )
    )
    return list(r.scalars())


async def solicitar(
    sessao: AsyncSession, *, desbloqueio_id: UUID, usuario_id: UUID,
    agora: datetime | None = None,
) -> DesbloqueioRecompensa:
    """Quem ganhou pede o prêmio."""
    d = await sessao.get(DesbloqueioRecompensa, desbloqueio_id)
    if d is None or d.beneficiario_id != usuario_id:
        raise NaoEncontrado("Prêmio não encontrado.")
    if d.status != StatusRecompensa.DESBLOQUEADA:
        raise SemPermissao("Este prêmio não está disponível para solicitação.")

    d.status = StatusRecompensa.SOLICITADA
    d.solicitado_em = agora or datetime.now(UTC)
    await sessao.flush()
    return d


async def confirmar_entrega(
    sessao: AsyncSession, *, desbloqueio_id: UUID, vinculo: MembroFamilia,
    agora: datetime | None = None,
) -> DesbloqueioRecompensa:
    """O responsável confirma que entregou — o ciclo fecha fora do app."""
    if vinculo.papel != PapelFamiliar.ADMIN:
        raise SemPermissao("Apenas o responsável confirma a entrega.")

    d = await sessao.get(DesbloqueioRecompensa, desbloqueio_id)
    if d is None:
        raise NaoEncontrado("Prêmio não encontrado.")

    nivel = await sessao.get(NivelRecompensa, d.nivel_id)
    trilha = await sessao.get(TrilhaRecompensa, nivel.trilha_id) if nivel else None
    if trilha is None or trilha.familia_id != vinculo.familia_id:
        raise NaoEncontrado("Prêmio não encontrado.")

    d.status = StatusRecompensa.ENTREGUE
    d.entregue_em = agora or datetime.now(UTC)
    d.confirmado_por_id = vinculo.usuario_id
    await sessao.flush()
    return d
