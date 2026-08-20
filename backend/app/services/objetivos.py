"""CRUD de objetivos, com as regras de quem pode o quê.

Autorização em uma frase: **só administrador cadastra objetivo**, e só
para alguém da própria família. Dependente executa o que foi cadastrado
para ele — quem decide o que ele vai estudar é o responsável (seção 7).
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NaoEncontrado, SemPermissao
from app.models.enums import PapelFamiliar, StatusObjetivo, StatusOcorrencia
from app.models.identidade import MembroFamilia
from app.models.objetivos import Materia, Objetivo, Ocorrencia
from app.repositories import usuarios as repo_usuarios


async def _exigir_titular_da_familia(
    sessao: AsyncSession, titular_id: UUID, familia_id: UUID
) -> None:
    if await repo_usuarios.vinculo_na_familia(sessao, titular_id, familia_id) is None:
        raise SemPermissao("Esta pessoa não faz parte da sua família.")


async def _exigir_materia_da_familia(
    sessao: AsyncSession, materia_id: UUID | None, familia_id: UUID
) -> None:
    """Sem isso, um objetivo poderia apontar pra matéria de outra família
    — a FK sozinha não impede, só garante que o id existe em algum lugar."""
    if materia_id is None:
        return
    materia = await sessao.get(Materia, materia_id)
    if materia is None or materia.familia_id != familia_id:
        raise NaoEncontrado("Matéria não encontrada.")


async def criar(
    sessao: AsyncSession, *, vinculo: MembroFamilia, dados: dict, titular_id: UUID | None
) -> Objetivo:
    if vinculo.papel != PapelFamiliar.ADMIN:
        raise SemPermissao("Apenas o responsável cadastra objetivos.")

    alvo = titular_id or vinculo.usuario_id
    if alvo != vinculo.usuario_id:
        await _exigir_titular_da_familia(sessao, alvo, vinculo.familia_id)
    await _exigir_materia_da_familia(sessao, dados.get("materia_id"), vinculo.familia_id)

    objetivo = Objetivo(
        familia_id=vinculo.familia_id,
        titular_id=alvo,
        criador_id=vinculo.usuario_id,
        **dados,
    )
    sessao.add(objetivo)
    await sessao.flush()
    return objetivo


async def obter(
    sessao: AsyncSession, *, objetivo_id: UUID, vinculo: MembroFamilia
) -> Objetivo:
    """Busca conferindo a família.

    O 404 para objetivo de outra família é proposital: um 403 confirmaria
    que aquele id existe.
    """
    objetivo = await sessao.get(Objetivo, objetivo_id)
    if objetivo is None or objetivo.familia_id != vinculo.familia_id:
        raise NaoEncontrado("Objetivo não encontrado.")

    # Dependente só enxerga o que é dele.
    if vinculo.papel == PapelFamiliar.DEPENDENTE and objetivo.titular_id != vinculo.usuario_id:
        raise NaoEncontrado("Objetivo não encontrado.")
    return objetivo


async def listar(
    sessao: AsyncSession,
    *,
    vinculo: MembroFamilia,
    titular_id: UUID | None = None,
    incluir_arquivados: bool = False,
) -> list[Objetivo]:
    consulta = select(Objetivo).where(Objetivo.familia_id == vinculo.familia_id)

    if vinculo.papel == PapelFamiliar.DEPENDENTE:
        consulta = consulta.where(Objetivo.titular_id == vinculo.usuario_id)
    elif titular_id is not None:
        consulta = consulta.where(Objetivo.titular_id == titular_id)

    if not incluir_arquivados:
        consulta = consulta.where(Objetivo.status != StatusObjetivo.ARQUIVADO)

    r = await sessao.execute(consulta.order_by(Objetivo.criado_em))
    return list(r.scalars())


async def editar(
    sessao: AsyncSession, *, objetivo: Objetivo, vinculo: MembroFamilia, mudancas: dict
) -> Objetivo:
    if vinculo.papel != PapelFamiliar.ADMIN:
        raise SemPermissao("Apenas o responsável edita objetivos.")
    if "materia_id" in mudancas:
        await _exigir_materia_da_familia(sessao, mudancas["materia_id"], vinculo.familia_id)
    for campo, valor in mudancas.items():
        setattr(objetivo, campo, valor)
    await sessao.flush()
    return objetivo


async def arquivar(
    sessao: AsyncSession, *, objetivo: Objetivo, vinculo: MembroFamilia
) -> Objetivo:
    """Arquiva em vez de apagar.

    A seção 8.5 é explícita: objetivo com sessões ou pontos nunca é
    apagado silenciosamente. Apagar levaria junto o histórico que
    justifica os pontos já creditados.
    """
    if vinculo.papel != PapelFamiliar.ADMIN:
        raise SemPermissao("Apenas o responsável arquiva objetivos.")

    objetivo.status = StatusObjetivo.ARQUIVADO
    objetivo.arquivado_em = datetime.now(UTC)

    # As obrigações futuras somem da fila; as concluídas ficam no histórico.
    r = await sessao.execute(
        select(Ocorrencia).where(
            Ocorrencia.objetivo_id == objetivo.id,
            Ocorrencia.status == StatusOcorrencia.PENDENTE,
        )
    )
    for o in r.scalars():
        await sessao.delete(o)

    await sessao.flush()
    return objetivo


async def excluir(
    sessao: AsyncSession, *, objetivo: Objetivo, vinculo: MembroFamilia
) -> bool:
    """Exclui de fato — só se não houver histórico. Devolve False se arquivou."""
    if vinculo.papel != PapelFamiliar.ADMIN:
        raise SemPermissao("Apenas o responsável exclui objetivos.")

    from app.models.pontos import LancamentoPontos

    tem_pontos = await sessao.execute(
        select(LancamentoPontos.id).where(LancamentoPontos.objetivo_id == objetivo.id).limit(1)
    )
    tem_conclusao = await sessao.execute(
        select(Ocorrencia.id).where(
            Ocorrencia.objetivo_id == objetivo.id,
            Ocorrencia.status == StatusOcorrencia.CONCLUIDA,
        ).limit(1)
    )
    if tem_pontos.first() or tem_conclusao.first():
        await arquivar(sessao, objetivo=objetivo, vinculo=vinculo)
        return False

    await sessao.delete(objetivo)
    await sessao.flush()
    return True
