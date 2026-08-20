"""Endpoints de matérias."""

from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import Sessao, VinculoAtual
from app.schemas.materias import CriarMateria, EditarMateria, MateriaPublica
from app.services import materias as servico

router = APIRouter(tags=["matérias"])


@router.post("/materias", response_model=MateriaPublica, status_code=status.HTTP_201_CREATED)
async def criar_materia(dados: CriarMateria, vinculo: VinculoAtual, sessao: Sessao):
    materia = await servico.criar(sessao, vinculo=vinculo, **dados.model_dump())
    await sessao.commit()
    return MateriaPublica.model_validate(materia)


@router.get("/materias", response_model=list[MateriaPublica])
async def listar_materias(vinculo: VinculoAtual, sessao: Sessao, incluir_inativas: bool = False):
    lista = await servico.listar(
        sessao, familia_id=vinculo.familia_id, incluir_inativas=incluir_inativas
    )
    return [MateriaPublica.model_validate(m) for m in lista]


@router.patch("/materias/{materia_id}", response_model=MateriaPublica)
async def editar_materia(
    materia_id: UUID, dados: EditarMateria, vinculo: VinculoAtual, sessao: Sessao
):
    materia = await servico.obter(sessao, materia_id=materia_id, familia_id=vinculo.familia_id)
    materia = await servico.editar(
        sessao, materia=materia, vinculo=vinculo, mudancas=dados.model_dump(exclude_unset=True)
    )
    await sessao.commit()
    return MateriaPublica.model_validate(materia)


@router.delete("/materias/{materia_id}", status_code=status.HTTP_204_NO_CONTENT)
async def arquivar_materia(materia_id: UUID, vinculo: VinculoAtual, sessao: Sessao):
    """Arquiva em vez de excluir — ver services/materias.py."""
    materia = await servico.obter(sessao, materia_id=materia_id, familia_id=vinculo.familia_id)
    await servico.arquivar(sessao, materia=materia, vinculo=vinculo)
    await sessao.commit()
