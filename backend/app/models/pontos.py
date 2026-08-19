"""Livro-razão de pontos, trilhas de recompensa, notificações e auditoria."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer,
    SmallInteger, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ENUM, INET, JSONB, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, PKUUID, Timestamps
from app.models.enums import EscopoTrilha, OrigemPontos, StatusRecompensa


class LancamentoPontos(PKUUID, Base):
    """Livro-razão de pontos — só insere, nunca atualiza nem apaga.

    O total de um usuário é a soma das linhas, não um campo que alguém
    incrementa. Isso resolve três problemas de uma vez: dá para auditar
    de onde veio cada ponto, um ajuste manual fica registrado como
    lançamento próprio, e não existe estado corrompido por atualização
    concorrente.

    `chave_idempotencia` impede creditar duas vezes o mesmo evento
    quando o Android reenvia a finalização de uma sessão.
    """

    __tablename__ = "point_ledger"

    beneficiario_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    familia_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), nullable=False
    )
    objetivo_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("objectives.id", ondelete="SET NULL")
    )
    materia_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("subjects.id", ondelete="SET NULL")
    )
    sessao_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("study_sessions.id", ondelete="SET NULL")
    )
    ocorrencia_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("objective_occurrences.id", ondelete="SET NULL")
    )

    # Aceita negativo: um estorno é um lançamento, não uma exclusão.
    pontos: Mapped[int] = mapped_column(Integer, nullable=False)
    origem: Mapped[OrigemPontos] = mapped_column(
        ENUM(OrigemPontos, name="origem_pontos", create_type=True), nullable=False
    )
    descricao: Mapped[str | None] = mapped_column(String(200))
    criado_por_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    chave_idempotencia: Mapped[str | None] = mapped_column(String(80), unique=True)

    __table_args__ = (
        CheckConstraint("pontos <> 0", name="lancamento_nao_pode_ser_zero"),
        Index("ix_ledger_beneficiario_data", "beneficiario_id", "criado_em"),
        Index("ix_ledger_familia_data", "familia_id", "criado_em"),
        Index("ix_ledger_materia", "materia_id"),
    )


class TrilhaRecompensa(PKUUID, Timestamps, Base):
    __tablename__ = "reward_tracks"

    beneficiario_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    familia_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), nullable=False
    )
    criador_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    escopo: Mapped[EscopoTrilha] = mapped_column(
        ENUM(EscopoTrilha, name="escopo_trilha", create_type=True), nullable=False
    )
    # Quais matérias ou objetivos entram na conta, conforme o escopo.
    filtro: Mapped[dict | None] = mapped_column(JSONB)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    niveis: Mapped[list["NivelRecompensa"]] = relationship(back_populates="trilha")

    __table_args__ = (Index("ix_tracks_beneficiario", "beneficiario_id"),)


class NivelRecompensa(PKUUID, Timestamps, Base):
    __tablename__ = "reward_levels"

    trilha_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("reward_tracks.id", ondelete="CASCADE"),
        nullable=False,
    )
    numero: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    pontos_necessarios: Mapped[int] = mapped_column(Integer, nullable=False)
    premio: Mapped[str] = mapped_column(String(200), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    trilha: Mapped["TrilhaRecompensa"] = relationship(back_populates="niveis")

    __table_args__ = (
        UniqueConstraint("trilha_id", "numero", name="nivel_unico_na_trilha"),
        CheckConstraint("pontos_necessarios > 0", name="pontos_positivos"),
        CheckConstraint("numero > 0", name="numero_positivo"),
    )


class DesbloqueioRecompensa(PKUUID, Timestamps, Base):
    """Prêmio alcançado.

    Desbloquear não desconta pontos: o total é acumulativo e os níveis
    seguintes continuam alcançáveis (seção 10.2). O responsável confirma
    a entrega, o que fecha o ciclo fora do aplicativo.
    """

    __tablename__ = "reward_unlocks"

    nivel_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("reward_levels.id", ondelete="CASCADE"),
        nullable=False,
    )
    beneficiario_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[StatusRecompensa] = mapped_column(
        ENUM(StatusRecompensa, name="status_recompensa", create_type=True),
        default=StatusRecompensa.DESBLOQUEADA, nullable=False,
    )
    desbloqueado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    solicitado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    entregue_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmado_por_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    __table_args__ = (
        # Um nível só desbloqueia uma vez por pessoa.
        UniqueConstraint("nivel_id", "beneficiario_id", name="desbloqueio_unico"),
    )


class Notificacao(PKUUID, Base):
    __tablename__ = "notifications"

    destinatario_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    familia_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), nullable=False
    )
    tipo: Mapped[str] = mapped_column(String(60), nullable=False)
    titulo: Mapped[str] = mapped_column(String(160), nullable=False)
    mensagem: Mapped[str] = mapped_column(Text, nullable=False)
    dados: Mapped[dict | None] = mapped_column(JSONB)
    lida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        # Índice parcial: a consulta frequente é "não lidas deste usuário".
        Index(
            "ix_notifications_nao_lidas",
            "destinatario_id", "criada_em",
            postgresql_where=lida_em.is_(None),
        ),
    )


class RegistroAuditoria(PKUUID, Base):
    """Quem fez o quê.

    Existe principalmente para o acesso administrativo às capturas: se o
    responsável abre a captura de um dependente, fica registrado. Um
    sistema que observa alguém precisa ele próprio ser observável.
    """

    __tablename__ = "audit_logs"

    ator_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    familia_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("families.id", ondelete="SET NULL")
    )
    acao: Mapped[str] = mapped_column(String(80), nullable=False)
    recurso_tipo: Mapped[str] = mapped_column(String(60), nullable=False)
    recurso_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True))
    # Nunca guardar token, senha ou coordenada completa aqui (seção 23).
    metadados: Mapped[dict | None] = mapped_column(JSONB)
    ip: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)
    ocorrido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_audit_familia_tempo", "familia_id", "ocorrido_em"),
        Index("ix_audit_recurso", "recurso_tipo", "recurso_id"),
    )
