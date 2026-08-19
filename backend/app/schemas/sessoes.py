"""Contratos das sessões de estudo."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EstadoSessao, TipoSessao


class AbrirSessao(BaseModel):
    objetivo_id: UUID
    ocorrencia_id: UUID | None = None
    dispositivo_id: UUID | None = None
    # Só o Android consegue sustentar sessão verificada. A web pedindo
    # isso recebe 403 — melhor recusar do que fingir que monitora.
    verificada: bool = False


class Heartbeat(BaseModel):
    """Aviso de que o aparelho continua vivo.

    Não carrega tempo: quem mede é o servidor, pela diferença entre dois
    avisos. O cliente só informa o que está conseguindo fazer.
    """

    capturando: bool = False
    localizando: bool = False


class FinalizarSessao(BaseModel):
    resumo: str | None = Field(default=None, max_length=2000)
    # Chave gerada pelo cliente. Reenviar o encerramento com a mesma
    # chave não credita de novo.
    chave_finalizacao: str | None = Field(default=None, max_length=64)


class SessaoPublica(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    objetivo_id: UUID
    ocorrencia_id: UUID | None
    usuario_id: UUID
    tipo: TipoSessao
    estado: EstadoSessao
    iniciada_em: datetime
    finalizada_em: datetime | None
    ultimo_heartbeat_em: datetime | None
    segundos_brutos: int
    segundos_validos: int
    segundos_verificados: int
    segundos_nao_verificados: int
    motivo_interrupcao: str | None
    exige_captura: bool
    exige_localizacao: bool
    intervalo_captura_seg: int | None


class RespostaHeartbeat(BaseModel):
    sessao: SessaoPublica
    segundos_creditados: int
    houve_lacuna: bool
    lacuna_segundos: int


class RespostaFinal(BaseModel):
    sessao: SessaoPublica
    minutos_validos: int
    minutos_verificados: int
    ocorrencia_concluida: bool
    pontos_creditados: int
