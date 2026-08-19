"""Matérias, objetivos e ocorrências.

A separação entre objetivo e ocorrência é o ponto central da seção 9 da
especificação:

- **Objetivo** é a regra: "inglês, 40 minutos, de segunda a sexta".
- **Ocorrência** é a obrigação concreta: "aula 12, prevista para 21/08".

Sem essa separação não há como registrar que algo foi adiantado, nem
impedir que a mesma aula reapareça na data original depois de concluída.
"""

from datetime import date, datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import PKUUID, Base, Timestamps
from app.db.tipos import JSONB_PORTATIL
from app.models.enums import (
    Frequencia,
    MomentoConclusao,
    StatusObjetivo,
    StatusOcorrencia,
    TipoObjetivo,
)


class Materia(PKUUID, Timestamps, Base):
    __tablename__ = "subjects"

    familia_id: Mapped[UUID] = mapped_column(
        sa.Uuid(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), nullable=False
    )
    nome: Mapped[str] = mapped_column(String(80), nullable=False)
    cor: Mapped[str | None] = mapped_column(String(7))
    icone: Mapped[str | None] = mapped_column(String(40))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("familia_id", "nome", name="materia_unica_por_familia"),
    )


class Objetivo(PKUUID, Timestamps, Base):
    __tablename__ = "objectives"

    familia_id: Mapped[UUID] = mapped_column(
        sa.Uuid(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), nullable=False
    )
    # Titular é quem cumpre; criador é quem cadastrou. São diferentes
    # quando o responsável cadastra um objetivo para o dependente.
    titular_id: Mapped[UUID] = mapped_column(
        sa.Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    criador_id: Mapped[UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    materia_id: Mapped[UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True), ForeignKey("subjects.id", ondelete="SET NULL")
    )

    tipo: Mapped[TipoObjetivo] = mapped_column(
        sa.Enum(TipoObjetivo, name="tipo_objetivo"), nullable=False
    )
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text)

    # Estudo guarda minutos; tarefa guarda quantidade de vezes. Um inteiro
    # só, e não float, para não acumular erro de arredondamento nos pontos.
    meta_periodo: Mapped[int] = mapped_column(Integer, nullable=False)
    meta_total: Mapped[int | None] = mapped_column(Integer)

    frequencia: Mapped[Frequencia] = mapped_column(
        sa.Enum(Frequencia, name="frequencia"), nullable=False
    )
    dias_semana: Mapped[list[int] | None] = mapped_column(JSONB_PORTATIL)   # 0=domingo
    horario_sugerido: Mapped[str | None] = mapped_column(String(5))
    inicia_em: Mapped[date | None] = mapped_column(Date)
    prazo_final: Mapped[date | None] = mapped_column(Date)

    acumula_pendencia: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    permite_adiantar: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_adiantamentos: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    adiantamento_exige_aprovacao: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    exige_sessao_verificada: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    limite_pontos_dia: Mapped[int | None] = mapped_column(Integer)
    pontos_fixos: Mapped[int | None] = mapped_column(Integer)
    exige_aprovacao_final: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    status: Mapped[StatusObjetivo] = mapped_column(
        sa.Enum(StatusObjetivo, name="status_objetivo"),
        default=StatusObjetivo.ANDAMENTO, nullable=False,
    )
    arquivado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    ocorrencias: Mapped[list["Ocorrencia"]] = relationship(back_populates="objetivo")

    __table_args__ = (
        CheckConstraint("meta_periodo > 0", name="meta_positiva"),
        CheckConstraint("meta_total IS NULL OR meta_total > 0", name="total_positivo"),
        CheckConstraint("max_adiantamentos BETWEEN 0 AND 30", name="adiantamento_razoavel"),
        CheckConstraint(
            "prazo_final IS NULL OR inicia_em IS NULL OR prazo_final >= inicia_em",
            name="prazo_depois_do_inicio",
        ),
        # Tarefa sem cronômetro precisa de pontuação fixa, senão concluí-la
        # não geraria ponto nenhum.
        CheckConstraint(
            "tipo <> 'task' OR pontos_fixos IS NOT NULL", name="tarefa_tem_pontos_fixos"
        ),
        Index("ix_objectives_titular_status", "titular_id", "status"),
        Index("ix_objectives_familia", "familia_id"),
    )


class Ocorrencia(PKUUID, Timestamps, Base):
    __tablename__ = "objective_occurrences"

    objetivo_id: Mapped[UUID] = mapped_column(
        sa.Uuid(as_uuid=True), ForeignKey("objectives.id", ondelete="CASCADE"), nullable=False
    )
    titular_id: Mapped[UUID] = mapped_column(
        sa.Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    prevista_para: Mapped[date] = mapped_column(Date, nullable=False)
    meta: Mapped[int] = mapped_column(Integer, nullable=False)
    realizado: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    status: Mapped[StatusOcorrencia] = mapped_column(
        sa.Enum(StatusOcorrencia, name="status_ocorrencia"),
        default=StatusOcorrencia.PENDENTE, nullable=False,
    )
    concluida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    momento_conclusao: Mapped[MomentoConclusao | None] = mapped_column(
        sa.Enum(MomentoConclusao, name="momento_conclusao")
    )
    dias_adiantados: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    # Ciclo proposital: a ocorrencia aponta para a sessao que a concluiu e
    # a sessao aponta para a ocorrencia que estava cumprindo. O PostgreSQL
    # nao consegue criar as duas tabelas com as duas FKs numa passada, entao
    # `use_alter` faz esta constraint ser adicionada por ALTER TABLE depois
    # que ambas existem. Sem isso a migracao inicial falha.
    sessao_conclusao_id: Mapped[UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True),
        ForeignKey(
            "study_sessions.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_occurrence_sessao_conclusao",
        ),
    )

    objetivo: Mapped["Objetivo"] = relationship(back_populates="ocorrencias")

    __table_args__ = (
        # Impede gerar a mesma aula duas vezes para a mesma data — a
        # proteção que faz o adiantamento não duplicar a obrigação.
        UniqueConstraint("objetivo_id", "prevista_para", name="ocorrencia_unica_por_data"),
        CheckConstraint("realizado >= 0", name="realizado_nao_negativo"),
        CheckConstraint("dias_adiantados >= 0", name="adiantamento_nao_negativo"),
        Index("ix_occurrences_titular_data", "titular_id", "prevista_para"),
        Index("ix_occurrences_status_data", "status", "prevista_para"),
    )
