"""Contratos dos painéis e recompensas."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EscopoTrilha, StatusRecompensa


class ResumoUsuario(BaseModel):
    usuario_id: UUID
    nome: str
    pontos_totais: int
    pontos_por_materia: dict[str, int]
    minutos_hoje: int
    minutos_semana: int
    minutos_mes: int
    sequencia_dias: int
    concluidas_hoje: int
    atrasadas: int
    pendentes_hoje: int
    estado_sessao: str | None


class MetaDoDia(BaseModel):
    meta: int
    realizado: int
    percentual: int


class PainelPessoal(BaseModel):
    resumo: ResumoUsuario
    meta_do_dia: MetaDoDia
    serie_semana: dict[date, int]
    serie_mes: dict[date, int]


class PainelFamiliar(BaseModel):
    eu: ResumoUsuario
    dependentes: list[ResumoUsuario]


class ItemHistorico(BaseModel):
    id: UUID
    quando: datetime
    pontos: int
    origem: str
    objetivo: str | None
    descricao: str | None


class CriarTrilha(BaseModel):
    beneficiario_id: UUID | None = None
    nome: str = Field(min_length=2, max_length=120)
    escopo: EscopoTrilha = EscopoTrilha.TODOS
    filtro: dict | None = None


class CriarNivel(BaseModel):
    pontos_necessarios: int = Field(gt=0)
    premio: str = Field(min_length=2, max_length=200)


class NivelPublico(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    numero: int
    pontos_necessarios: int
    premio: str


class ProgressoPublico(BaseModel):
    trilha_id: UUID
    nome: str
    escopo: EscopoTrilha
    pontos: int
    nivel_atual: NivelPublico | None
    proximo_nivel: NivelPublico | None
    faltam: int
    percentual: int
    niveis_desbloqueados: int


class PremioPublico(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nivel_id: UUID
    status: StatusRecompensa
    desbloqueado_em: datetime
    solicitado_em: datetime | None
    entregue_em: datetime | None
