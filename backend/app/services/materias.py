"""CRUD de matérias.

Mesma regra de autorização de objetivos: só o responsável cadastra,
edita ou arquiva — quem decide o que existe pra estudar é ele (seção 7).
Qualquer papel da família pode listar, porque o dependente precisa ver
a matéria ao executar um objetivo.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import JaExiste, NaoEncontrado, SemPermissao
from app.models.enums import PapelFamiliar
from app.models.identidade import MembroFamilia
from app.models.objetivos import Materia


async def _nome_disponivel(
    sessao: AsyncSession, *, familia_id: UUID, nome: str, exceto_id: UUID | None = None
) -> bool:
    consulta = select(Materia.id).where(Materia.familia_id == familia_id, Materia.nome == nome)
    if exceto_id is not None:
        consulta = consulta.where(Materia.id != exceto_id)
    r = await sessao.execute(consulta.limit(1))
    return r.first() is None


async def criar(
    sessao: AsyncSession, *, vinculo: MembroFamilia,
    nome: str, cor: str | None = None, icone: str | None = None,
) -> Materia:
    if vinculo.papel != PapelFamiliar.ADMIN:
        raise SemPermissao("Apenas o responsável cadastra matérias.")
    if not await _nome_disponivel(sessao, familia_id=vinculo.familia_id, nome=nome):
        raise JaExiste("Já existe uma matéria com esse nome.")

    materia = Materia(familia_id=vinculo.familia_id, nome=nome, cor=cor, icone=icone)
    sessao.add(materia)
    await sessao.flush()
    return materia


async def listar(
    sessao: AsyncSession, *, familia_id: UUID, incluir_inativas: bool = False
) -> list[Materia]:
    consulta = select(Materia).where(Materia.familia_id == familia_id)
    if not incluir_inativas:
        consulta = consulta.where(Materia.ativo.is_(True))
    r = await sessao.execute(consulta.order_by(Materia.nome))
    return list(r.scalars())


async def obter(sessao: AsyncSession, *, materia_id: UUID, familia_id: UUID) -> Materia:
    materia = await sessao.get(Materia, materia_id)
    if materia is None or materia.familia_id != familia_id:
        raise NaoEncontrado("Matéria não encontrada.")
    return materia


async def editar(
    sessao: AsyncSession, *, materia: Materia, vinculo: MembroFamilia, mudancas: dict
) -> Materia:
    if vinculo.papel != PapelFamiliar.ADMIN:
        raise SemPermissao("Apenas o responsável edita matérias.")
    novo_nome = mudancas.get("nome")
    if novo_nome and novo_nome != materia.nome:
        disponivel = await _nome_disponivel(
            sessao, familia_id=materia.familia_id, nome=novo_nome, exceto_id=materia.id
        )
        if not disponivel:
            raise JaExiste("Já existe uma matéria com esse nome.")
    for campo, valor in mudancas.items():
        setattr(materia, campo, valor)
    await sessao.flush()
    return materia


async def arquivar(sessao: AsyncSession, *, materia: Materia, vinculo: MembroFamilia) -> Materia:
    """Arquiva em vez de apagar: objetivos já cadastrados continuam
    apontando pro nome certo (mesmo raciocínio de objetivos.arquivar)."""
    if vinculo.papel != PapelFamiliar.ADMIN:
        raise SemPermissao("Apenas o responsável arquiva matérias.")
    materia.ativo = False
    await sessao.flush()
    return materia
