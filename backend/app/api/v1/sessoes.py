"""Endpoints das sessões de estudo."""

from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import Sessao, VinculoAtual
from app.core.exceptions import NaoEncontrado
from app.models.objetivos import Ocorrencia
from app.schemas.sessoes import (
    AbrirSessao,
    FinalizarSessao,
    Heartbeat,
    RespostaFinal,
    RespostaHeartbeat,
    SessaoPublica,
)
from app.services import objetivos as servico_objetivos
from app.services import sessoes as servico

router = APIRouter(prefix="/sessoes", tags=["sessões"])


@router.post("", response_model=SessaoPublica, status_code=status.HTTP_201_CREATED)
async def abrir(dados: AbrirSessao, vinculo: VinculoAtual, sessao: Sessao):
    objetivo = await servico_objetivos.obter(
        sessao, objetivo_id=dados.objetivo_id, vinculo=vinculo
    )
    ocorrencia = None
    if dados.ocorrencia_id:
        ocorrencia = await sessao.get(Ocorrencia, dados.ocorrencia_id)
        if ocorrencia is None or ocorrencia.objetivo_id != objetivo.id:
            raise NaoEncontrado("Atividade não encontrada para este objetivo.")

    se = await servico.abrir(
        sessao,
        objetivo=objetivo,
        ocorrencia=ocorrencia,
        usuario_id=vinculo.usuario_id,
        familia_id=vinculo.familia_id,
        papel=vinculo.papel,
        dispositivo_id=dados.dispositivo_id,
        verificada=dados.verificada,
    )
    await sessao.commit()
    return SessaoPublica.model_validate(se)


@router.get("/aberta", response_model=SessaoPublica | None)
async def aberta(vinculo: VinculoAtual, sessao: Sessao):
    """Sessão em andamento de quem chamou.

    É o que permite retomar o cronômetro depois de fechar o navegador: o
    estado vive no servidor, não na aba.
    """
    se = await servico.sessao_aberta_de(sessao, vinculo.usuario_id)
    return SessaoPublica.model_validate(se) if se else None


@router.get("/{sessao_id}", response_model=SessaoPublica)
async def obter(sessao_id: UUID, vinculo: VinculoAtual, sessao: Sessao):
    se = await servico.obter(
        sessao, sessao_id=sessao_id, usuario_id=vinculo.usuario_id,
        familia_id=vinculo.familia_id, papel=vinculo.papel,
    )
    return SessaoPublica.model_validate(se)


@router.post("/{sessao_id}/heartbeat", response_model=RespostaHeartbeat)
async def heartbeat(
    sessao_id: UUID, dados: Heartbeat, vinculo: VinculoAtual, sessao: Sessao
):
    se = await servico.obter(
        sessao, sessao_id=sessao_id, usuario_id=vinculo.usuario_id,
        familia_id=vinculo.familia_id, papel=vinculo.papel,
    )
    r = await servico.heartbeat(
        sessao, sessao_estudo=se,
        capturando=dados.capturando, localizando=dados.localizando,
    )
    await sessao.commit()
    return RespostaHeartbeat(
        sessao=SessaoPublica.model_validate(r.sessao),
        segundos_creditados=r.segundos_creditados,
        houve_lacuna=r.houve_lacuna,
        lacuna_segundos=r.lacuna_segundos,
    )


@router.post("/{sessao_id}/pausar", response_model=SessaoPublica)
async def pausar(sessao_id: UUID, vinculo: VinculoAtual, sessao: Sessao):
    se = await servico.obter(
        sessao, sessao_id=sessao_id, usuario_id=vinculo.usuario_id,
        familia_id=vinculo.familia_id, papel=vinculo.papel,
    )
    await servico.pausar(sessao, sessao_estudo=se)
    await sessao.commit()
    return SessaoPublica.model_validate(se)


@router.post("/{sessao_id}/retomar", response_model=SessaoPublica)
async def retomar(sessao_id: UUID, vinculo: VinculoAtual, sessao: Sessao):
    se = await servico.obter(
        sessao, sessao_id=sessao_id, usuario_id=vinculo.usuario_id,
        familia_id=vinculo.familia_id, papel=vinculo.papel,
    )
    await servico.retomar(sessao, sessao_estudo=se)
    await sessao.commit()
    return SessaoPublica.model_validate(se)


@router.post("/{sessao_id}/finalizar", response_model=RespostaFinal)
async def finalizar(
    sessao_id: UUID, dados: FinalizarSessao, vinculo: VinculoAtual, sessao: Sessao
):
    se = await servico.obter(
        sessao, sessao_id=sessao_id, usuario_id=vinculo.usuario_id,
        familia_id=vinculo.familia_id, papel=vinculo.papel,
    )
    r = await servico.finalizar(
        sessao, sessao_estudo=se, papel=vinculo.papel,
        resumo=dados.resumo, chave_finalizacao=dados.chave_finalizacao,
    )
    await sessao.commit()
    return RespostaFinal(
        sessao=SessaoPublica.model_validate(r.sessao),
        minutos_validos=r.minutos_validos,
        minutos_verificados=r.minutos_verificados,
        ocorrencia_concluida=r.ocorrencia_concluida,
        pontos_creditados=r.pontos_creditados,
    )
