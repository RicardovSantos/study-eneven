"""Contratos de objetivos e ocorrências."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import (
    Frequencia,
    MomentoConclusao,
    StatusObjetivo,
    StatusOcorrencia,
    TipoObjetivo,
)


class ObjetivoBase(BaseModel):
    tipo: TipoObjetivo
    nome: str = Field(min_length=2, max_length=160)
    descricao: str | None = None
    materia_id: UUID | None = None

    meta_periodo: int = Field(gt=0, description="minutos (estudo) ou vezes (tarefa)")
    meta_total: int | None = Field(default=None, gt=0)

    frequencia: Frequencia = Frequencia.DIARIA
    dias_semana: list[int] | None = Field(default=None, description="0=domingo")
    horario_sugerido: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    inicia_em: date | None = None
    prazo_final: date | None = None

    acumula_pendencia: bool = True
    permite_adiantar: bool = False
    max_adiantamentos: int = Field(default=1, ge=0, le=30)
    adiantamento_exige_aprovacao: bool = False

    exige_sessao_verificada: bool = False
    limite_pontos_dia: int | None = Field(default=None, gt=0)
    pontos_fixos: int | None = Field(default=None, gt=0)
    exige_aprovacao_final: bool = False

    @model_validator(mode="after")
    def _coerencias(self):
        if self.dias_semana and any(d < 0 or d > 6 for d in self.dias_semana):
            raise ValueError("dias_semana aceita apenas 0 a 6, com 0 = domingo")
        if self.prazo_final and self.inicia_em and self.prazo_final < self.inicia_em:
            raise ValueError("o prazo final não pode ser antes do início")
        # Tarefa não tem cronômetro: sem pontos fixos, concluí-la não
        # geraria ponto nenhum. O banco também recusa (CHECK).
        if self.tipo == TipoObjetivo.TAREFA and not self.pontos_fixos:
            raise ValueError("tarefa precisa de pontos_fixos")
        return self


class CriarObjetivo(ObjetivoBase):
    # Quem cumpre. Em branco = eu mesmo. Um responsável pode cadastrar
    # para um dependente da própria família; o serviço confere.
    titular_id: UUID | None = None


class EditarObjetivo(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=160)
    descricao: str | None = None
    materia_id: UUID | None = None
    meta_periodo: int | None = Field(default=None, gt=0)
    meta_total: int | None = Field(default=None, gt=0)
    dias_semana: list[int] | None = None
    horario_sugerido: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    prazo_final: date | None = None
    acumula_pendencia: bool | None = None
    permite_adiantar: bool | None = None
    max_adiantamentos: int | None = Field(default=None, ge=0, le=30)
    adiantamento_exige_aprovacao: bool | None = None
    exige_sessao_verificada: bool | None = None
    limite_pontos_dia: int | None = Field(default=None, gt=0)
    pontos_fixos: int | None = Field(default=None, gt=0)
    exige_aprovacao_final: bool | None = None
    status: StatusObjetivo | None = None


class ObjetivoPublico(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    familia_id: UUID
    titular_id: UUID
    materia_id: UUID | None
    tipo: TipoObjetivo
    nome: str
    descricao: str | None
    meta_periodo: int
    meta_total: int | None
    frequencia: Frequencia
    dias_semana: list[int] | None
    inicia_em: date | None
    prazo_final: date | None
    acumula_pendencia: bool
    permite_adiantar: bool
    max_adiantamentos: int
    exige_sessao_verificada: bool
    limite_pontos_dia: int | None
    pontos_fixos: int | None
    status: StatusObjetivo
    criado_em: datetime


class OcorrenciaPublica(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    objetivo_id: UUID
    titular_id: UUID
    prevista_para: date
    meta: int
    realizado: int
    status: StatusOcorrencia
    concluida_em: datetime | None
    momento_conclusao: MomentoConclusao | None
    dias_adiantados: int


class ProgressoOcorrencia(BaseModel):
    quantidade: int = Field(gt=0, description="minutos (estudo) ou repetições (tarefa)")


class ConcluirOcorrencia(BaseModel):
    minutos_validos: int = Field(default=0, ge=0)
    minutos_verificados: int = Field(default=0, ge=0)
    sessao_estudo_id: UUID | None = None

    @model_validator(mode="after")
    def _verificado_cabe_no_valido(self):
        if self.minutos_verificados > self.minutos_validos:
            raise ValueError("minutos_verificados não pode passar de minutos_validos")
        return self


class ResultadoConclusao(BaseModel):
    ocorrencia: OcorrenciaPublica
    pontos_creditados: int
    momento: MomentoConclusao


class ProximaAtividade(BaseModel):
    """O que a tela mostra depois de concluir: 'adiantar a próxima?'"""

    ocorrencia: OcorrenciaPublica | None
    pode_adiantar: bool
    motivo: str | None = None
