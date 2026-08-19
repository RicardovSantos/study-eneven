"""Sessões de estudo, eventos, capturas e localizações."""

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import PKUUID, Base, Timestamps
from app.db.tipos import JSONB_PORTATIL
from app.models.enums import EstadoSessao, StatusCaptura, TipoSessao


class SessaoEstudo(PKUUID, Timestamps, Base):
    """Sessão de foco.

    Os segundos são separados em quatro contagens porque não são a mesma
    coisa e a diferença importa para a confiança do responsável:

    - `segundos_brutos`: do início ao fim, incluindo pausas;
    - `segundos_validos`: o que conta como estudo (bruto menos pausas);
    - `segundos_verificados`: parte com captura e heartbeat funcionando;
    - `segundos_nao_verificados`: o resto — offline, permissão revogada.

    Uma sessão interrompida nunca vira 100% verificada: o tempo sem
    verificação fica registrado como tal.

    Todos os horários vêm do servidor. O relógio do aparelho é gravado
    à parte, só como referência — quem define a contagem é o servidor.
    """

    __tablename__ = "study_sessions"

    ocorrencia_id: Mapped[UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True), ForeignKey("objective_occurrences.id", ondelete="SET NULL")
    )
    objetivo_id: Mapped[UUID] = mapped_column(
        sa.Uuid(as_uuid=True), ForeignKey("objectives.id", ondelete="CASCADE"), nullable=False
    )
    usuario_id: Mapped[UUID] = mapped_column(
        sa.Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    familia_id: Mapped[UUID] = mapped_column(
        sa.Uuid(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), nullable=False
    )
    dispositivo_id: Mapped[UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True), ForeignKey("devices.id", ondelete="SET NULL")
    )

    tipo: Mapped[TipoSessao] = mapped_column(
        sa.Enum(TipoSessao, name="tipo_sessao"),
        default=TipoSessao.NORMAL, nullable=False,
    )
    estado: Mapped[EstadoSessao] = mapped_column(
        sa.Enum(EstadoSessao, name="estado_sessao"),
        default=EstadoSessao.ATIVA, nullable=False,
    )

    iniciada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    pausada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retomada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finalizada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ultimo_heartbeat_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    segundos_brutos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    segundos_validos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    segundos_verificados: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    segundos_nao_verificados: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    motivo_interrupcao: Mapped[str | None] = mapped_column(String(80))

    # Cópia da configuração no momento em que a sessão começou. Se o
    # responsável mudar o intervalo depois, o histórico continua contando
    # a verdade sobre como aquela sessão foi feita.
    exige_captura: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    exige_localizacao: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    intervalo_captura_seg: Mapped[int | None] = mapped_column(Integer)

    resumo_final: Mapped[str | None] = mapped_column(Text)
    aprovada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    aprovada_por_id: Mapped[UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    # Chave de idempotência: o Android pode reenviar a finalização depois
    # de perder a resposta. Com isso, o reenvio não credita pontos de novo.
    chave_finalizacao: Mapped[str | None] = mapped_column(String(64), unique=True)

    eventos: Mapped[list["EventoSessao"]] = relationship(
        back_populates="sessao", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        CheckConstraint("segundos_brutos >= 0", name="brutos_nao_negativos"),
        CheckConstraint("segundos_validos >= 0", name="validos_nao_negativos"),
        CheckConstraint(
            "segundos_validos <= segundos_brutos", name="validos_cabem_no_bruto"
        ),
        CheckConstraint(
            "segundos_verificados + segundos_nao_verificados <= segundos_brutos",
            name="verificado_cabe_no_bruto",
        ),
        CheckConstraint(
            "finalizada_em IS NULL OR finalizada_em >= iniciada_em",
            name="fim_depois_do_inicio",
        ),
        Index("ix_sessions_usuario_inicio", "usuario_id", "iniciada_em"),
        Index("ix_sessions_familia_estado", "familia_id", "estado"),
        Index("ix_sessions_objetivo", "objetivo_id"),
    )


class EventoSessao(PKUUID, Base):
    """Trilha do que aconteceu durante a sessão.

    Só insere, nunca atualiza: é o registro auditável que permite
    reconstruir a sessão se a contagem for contestada.
    """

    __tablename__ = "session_events"

    sessao_id: Mapped[UUID] = mapped_column(
        sa.Uuid(as_uuid=True), ForeignKey("study_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    tipo: Mapped[str] = mapped_column(String(60), nullable=False)
    ocorrido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    dados: Mapped[dict | None] = mapped_column(JSONB_PORTATIL)
    origem: Mapped[str] = mapped_column(String(20), nullable=False)   # web, android, servidor
    sequencia: Mapped[int] = mapped_column(BigInteger, nullable=False)

    sessao: Mapped["SessaoEstudo"] = relationship(back_populates="eventos")

    __table_args__ = (
        UniqueConstraint("sessao_id", "sequencia", name="sequencia_unica_na_sessao"),
        Index("ix_session_events_sessao_tempo", "sessao_id", "ocorrido_em"),
    )


class LocalConhecido(PKUUID, Timestamps, Base):
    """Geofence nomeada: casa da avó, escola, casa do responsável."""

    __tablename__ = "known_locations"

    familia_id: Mapped[UUID] = mapped_column(
        sa.Uuid(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), nullable=False
    )
    nome: Mapped[str] = mapped_column(String(80), nullable=False)
    latitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    raio_metros: Mapped[int] = mapped_column(Integer, default=150, nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("familia_id", "nome", name="local_unico_por_familia"),
        CheckConstraint("latitude BETWEEN -90 AND 90", name="latitude_valida"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="longitude_valida"),
        CheckConstraint("raio_metros BETWEEN 20 AND 5000", name="raio_razoavel"),
    )


class CapturaTela(PKUUID, Base):
    """Captura de tela de uma sessão verificada.

    O arquivo fica em volume privado; aqui só o caminho interno e os
    metadados. O hash SHA-256 serve para detectar reenvio duplicado e
    para provar que o arquivo não foi trocado depois.
    """

    __tablename__ = "screen_captures"

    sessao_id: Mapped[UUID] = mapped_column(
        sa.Uuid(as_uuid=True), ForeignKey("study_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    usuario_id: Mapped[UUID] = mapped_column(
        sa.Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    familia_id: Mapped[UUID] = mapped_column(
        sa.Uuid(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), nullable=False
    )

    caminho: Mapped[str] = mapped_column(String(500), nullable=False)
    caminho_miniatura: Mapped[str | None] = mapped_column(String(500))
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    bytes_tamanho: Mapped[int] = mapped_column(Integer, nullable=False)
    mime: Mapped[str] = mapped_column(String(40), nullable=False)
    largura: Mapped[int | None] = mapped_column(Integer)
    altura: Mapped[int | None] = mapped_column(Integer)

    capturada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recebida_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[StatusCaptura] = mapped_column(
        sa.Enum(StatusCaptura, name="status_captura"),
        default=StatusCaptura.RECEBIDA, nullable=False,
    )

    # Quando o Android detecta tela protegida (banco, streaming) o frame
    # sai preto. Marcar é mais honesto do que guardar imagem vazia.
    tela_protegida: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    remover_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("sessao_id", "sha256", name="captura_sem_duplicata"),
        CheckConstraint("bytes_tamanho > 0", name="tamanho_positivo"),
        Index("ix_captures_sessao_tempo", "sessao_id", "capturada_em"),
        Index("ix_captures_expiracao", "remover_em"),
    )


class LocalizacaoSessao(PKUUID, Base):
    __tablename__ = "session_locations"

    sessao_id: Mapped[UUID] = mapped_column(
        sa.Uuid(as_uuid=True), ForeignKey("study_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    captura_id: Mapped[UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True), ForeignKey("screen_captures.id", ondelete="SET NULL")
    )
    local_conhecido_id: Mapped[UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True), ForeignKey("known_locations.id", ondelete="SET NULL")
    )

    latitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    precisao_metros: Mapped[float | None] = mapped_column(Numeric(7, 2))

    medida_em_dispositivo: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recebida_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    idade_leitura_seg: Mapped[int | None] = mapped_column(Integer)

    # O Android informa quando a leitura veio de um provedor simulado.
    # É indício, não prova: localização é evidência contextual.
    simulada: Mapped[bool | None] = mapped_column(Boolean)

    __table_args__ = (
        CheckConstraint("latitude BETWEEN -90 AND 90", name="latitude_valida"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="longitude_valida"),
        Index("ix_locations_sessao", "sessao_id"),
    )
