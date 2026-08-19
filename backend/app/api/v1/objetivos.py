"""Endpoints de objetivos e ocorrências."""

from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import Sessao, VinculoAtual
from app.core.exceptions import NaoEncontrado
from app.models.objetivos import Ocorrencia
from app.schemas.objetivos import (
    ConcluirOcorrencia,
    CriarObjetivo,
    EditarObjetivo,
    ObjetivoPublico,
    OcorrenciaPublica,
    ProgressoOcorrencia,
    ProximaAtividade,
    ResultadoConclusao,
)
from app.services import agenda
from app.services import objetivos as servico
from app.services import ocorrencias as servico_oc

router = APIRouter(tags=["objetivos"])


# ---------- objetivos ----------

@router.post("/objetivos", response_model=ObjetivoPublico, status_code=status.HTTP_201_CREATED)
async def criar_objetivo(dados: CriarObjetivo, vinculo: VinculoAtual, sessao: Sessao):
    campos = dados.model_dump(exclude={"titular_id"})
    objetivo = await servico.criar(
        sessao, vinculo=vinculo, dados=campos, titular_id=dados.titular_id
    )
    # Já materializa a agenda: sem isso o objetivo nasceria sem nenhuma
    # obrigação e não apareceria na tela Estudar.
    await agenda.gerar_para_objetivo(sessao, objetivo)
    await sessao.commit()
    return ObjetivoPublico.model_validate(objetivo)


@router.get("/objetivos", response_model=list[ObjetivoPublico])
async def listar_objetivos(
    vinculo: VinculoAtual,
    sessao: Sessao,
    titular_id: UUID | None = None,
    incluir_arquivados: bool = False,
):
    lista = await servico.listar(
        sessao, vinculo=vinculo, titular_id=titular_id,
        incluir_arquivados=incluir_arquivados,
    )
    return [ObjetivoPublico.model_validate(o) for o in lista]


@router.get("/objetivos/{objetivo_id}", response_model=ObjetivoPublico)
async def obter_objetivo(objetivo_id: UUID, vinculo: VinculoAtual, sessao: Sessao):
    objetivo = await servico.obter(sessao, objetivo_id=objetivo_id, vinculo=vinculo)
    return ObjetivoPublico.model_validate(objetivo)


@router.patch("/objetivos/{objetivo_id}", response_model=ObjetivoPublico)
async def editar_objetivo(
    objetivo_id: UUID, dados: EditarObjetivo, vinculo: VinculoAtual, sessao: Sessao
):
    objetivo = await servico.obter(sessao, objetivo_id=objetivo_id, vinculo=vinculo)
    objetivo = await servico.editar(
        sessao, objetivo=objetivo, vinculo=vinculo,
        mudancas=dados.model_dump(exclude_unset=True),
    )
    await sessao.commit()
    return ObjetivoPublico.model_validate(objetivo)


@router.delete("/objetivos/{objetivo_id}")
async def excluir_objetivo(objetivo_id: UUID, vinculo: VinculoAtual, sessao: Sessao):
    """Exclui de fato só quando não há histórico; caso contrário, arquiva."""
    objetivo = await servico.obter(sessao, objetivo_id=objetivo_id, vinculo=vinculo)
    excluido = await servico.excluir(sessao, objetivo=objetivo, vinculo=vinculo)
    await sessao.commit()
    return {
        "excluido": excluido,
        "detalhe": (
            "Objetivo excluído."
            if excluido
            else "O objetivo tem histórico, então foi arquivado em vez de excluído."
        ),
    }


# ---------- ocorrências ----------

@router.get("/ocorrencias", response_model=list[OcorrenciaPublica])
async def listar_ocorrencias(
    vinculo: VinculoAtual,
    sessao: Sessao,
    de: date | None = None,
    ate: date | None = None,
    titular_id: UUID | None = None,
):
    """Agenda do período. Materializa o que faltar antes de responder."""
    from sqlalchemy import select

    from app.models.enums import PapelFamiliar
    from app.models.objetivos import Objetivo

    alvo = vinculo.usuario_id
    if vinculo.papel == PapelFamiliar.ADMIN and titular_id is not None:
        alvo = titular_id

    hoje = date.today()
    de = de or hoje
    ate = ate or (hoje + timedelta(days=agenda.JANELA_PADRAO_DIAS))

    await agenda.gerar_para_titular(sessao, alvo, ate=ate)
    await agenda.marcar_perdidas(sessao, alvo)
    await sessao.commit()

    r = await sessao.execute(
        select(Ocorrencia)
        .join(Objetivo, Objetivo.id == Ocorrencia.objetivo_id)
        .where(
            Ocorrencia.titular_id == alvo,
            Objetivo.familia_id == vinculo.familia_id,
            Ocorrencia.prevista_para >= de,
            Ocorrencia.prevista_para <= ate,
        )
        .order_by(Ocorrencia.prevista_para)
    )
    return [OcorrenciaPublica.model_validate(o) for o in r.scalars()]


async def _ocorrencia_permitida(sessao, ocorrencia_id: UUID, vinculo) -> Ocorrencia:
    ocorrencia = await sessao.get(Ocorrencia, ocorrencia_id)
    if ocorrencia is None:
        raise NaoEncontrado("Atividade não encontrada.")
    # Passa pelo serviço de objetivos, que já confere família e titular.
    await servico.obter(sessao, objetivo_id=ocorrencia.objetivo_id, vinculo=vinculo)
    return ocorrencia


@router.post("/ocorrencias/{ocorrencia_id}/progresso", response_model=OcorrenciaPublica)
async def registrar_progresso(
    ocorrencia_id: UUID, dados: ProgressoOcorrencia, vinculo: VinculoAtual, sessao: Sessao
):
    ocorrencia = await _ocorrencia_permitida(sessao, ocorrencia_id, vinculo)
    await servico_oc.registrar_progresso(sessao, ocorrencia, dados.quantidade)
    await sessao.commit()
    return OcorrenciaPublica.model_validate(ocorrencia)


@router.post("/ocorrencias/{ocorrencia_id}/concluir", response_model=ResultadoConclusao)
async def concluir_ocorrencia(
    ocorrencia_id: UUID, dados: ConcluirOcorrencia, vinculo: VinculoAtual, sessao: Sessao
):
    ocorrencia = await _ocorrencia_permitida(sessao, ocorrencia_id, vinculo)
    objetivo = await servico.obter(
        sessao, objetivo_id=ocorrencia.objetivo_id, vinculo=vinculo
    )
    resultado = await servico_oc.concluir(
        sessao,
        ocorrencia=ocorrencia,
        objetivo=objetivo,
        familia_id=vinculo.familia_id,
        papel=vinculo.papel,
        minutos_validos=dados.minutos_validos,
        minutos_verificados=dados.minutos_verificados,
        sessao_estudo_id=dados.sessao_estudo_id,
    )
    await sessao.commit()
    return ResultadoConclusao(
        ocorrencia=OcorrenciaPublica.model_validate(resultado.ocorrencia),
        pontos_creditados=resultado.pontos_creditados,
        momento=resultado.momento,
    )


@router.post("/ocorrencias/{ocorrencia_id}/desfazer", response_model=OcorrenciaPublica)
async def desfazer_conclusao(ocorrencia_id: UUID, vinculo: VinculoAtual, sessao: Sessao):
    ocorrencia = await _ocorrencia_permitida(sessao, ocorrencia_id, vinculo)
    objetivo = await servico.obter(
        sessao, objetivo_id=ocorrencia.objetivo_id, vinculo=vinculo
    )
    await servico_oc.desfazer(sessao, ocorrencia=ocorrencia, objetivo=objetivo)
    await sessao.commit()
    return OcorrenciaPublica.model_validate(ocorrencia)


@router.get("/ocorrencias/{ocorrencia_id}/proxima", response_model=ProximaAtividade)
async def proxima_atividade(ocorrencia_id: UUID, vinculo: VinculoAtual, sessao: Sessao):
    """Alimenta o 'Adiantar próxima aula?' que aparece após concluir."""
    ocorrencia = await _ocorrencia_permitida(sessao, ocorrencia_id, vinculo)
    objetivo = await servico.obter(
        sessao, objetivo_id=ocorrencia.objetivo_id, vinculo=vinculo
    )
    proxima = await servico_oc.proxima_pendente(
        sessao, objetivo.id, ocorrencia.prevista_para
    )
    if proxima is None:
        return ProximaAtividade(ocorrencia=None, pode_adiantar=False, motivo=None)

    pode, motivo = await servico_oc.pode_adiantar(sessao, objetivo, proxima, date.today())
    return ProximaAtividade(
        ocorrencia=OcorrenciaPublica.model_validate(proxima),
        pode_adiantar=pode,
        motivo=motivo or None,
    )
