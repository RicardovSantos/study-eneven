"""Usuários, famílias, vínculos, tokens e dispositivos."""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer,
    String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ENUM, INET, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, PKUUID, Timestamps
from app.models.enums import PapelFamiliar, Plataforma, StatusMembro


class Usuario(PKUUID, Timestamps, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    # Opcional porque um dependente pode ser criado sem e-mail próprio.
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nome_exibicao: Mapped[str] = mapped_column(String(120), nullable=False)
    avatar_caminho: Mapped[str | None] = mapped_column(String(500))
    nascimento: Mapped[date | None]
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ultimo_login_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    vinculos: Mapped[list["MembroFamilia"]] = relationship(
        back_populates="usuario", foreign_keys="MembroFamilia.usuario_id"
    )

    __table_args__ = (
        CheckConstraint("char_length(username) >= 3", name="username_minimo"),
        Index("ix_users_ativo", "ativo"),
    )


class Familia(PKUUID, Timestamps, Base):
    __tablename__ = "families"

    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    dono_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    # Padrões da família; cada objetivo pode sobrescrever o que faz sentido.
    intervalo_captura_seg: Mapped[int] = mapped_column(Integer, default=480, nullable=False)
    retencao_captura_dias: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    exige_localizacao: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    pontos_por_minuto: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    membros: Mapped[list["MembroFamilia"]] = relationship(back_populates="familia")

    __table_args__ = (
        CheckConstraint(
            "intervalo_captura_seg BETWEEN 60 AND 3600", name="intervalo_captura_razoavel"
        ),
        CheckConstraint(
            "retencao_captura_dias BETWEEN 1 AND 90", name="retencao_razoavel"
        ),
    )


class MembroFamilia(PKUUID, Timestamps, Base):
    """Vínculo entre usuário e família — é aqui que mora o papel.

    O papel fica no vínculo, e não no usuário, porque a mesma pessoa pode
    ser responsável na própria família e aparecer em outra depois. Toda
    autorização do backend consulta esta tabela, nunca o que o cliente
    afirma ser.
    """

    __tablename__ = "family_members"

    familia_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), nullable=False
    )
    usuario_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    papel: Mapped[PapelFamiliar] = mapped_column(
        ENUM(PapelFamiliar, name="papel_familiar", create_type=True), nullable=False
    )
    parentesco: Mapped[str | None] = mapped_column(String(60))
    status: Mapped[StatusMembro] = mapped_column(
        ENUM(StatusMembro, name="status_membro", create_type=True),
        default=StatusMembro.ATIVO, nullable=False,
    )
    criado_por_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    familia: Mapped["Familia"] = relationship(back_populates="membros")
    usuario: Mapped["Usuario"] = relationship(
        back_populates="vinculos", foreign_keys=[usuario_id]
    )

    __table_args__ = (
        UniqueConstraint("familia_id", "usuario_id", name="membro_unico_por_familia"),
        Index("ix_family_members_familia_papel", "familia_id", "papel"),
    )


class RefreshToken(PKUUID, Timestamps, Base):
    """Refresh token opaco e rotativo.

    Guarda só o hash: um vazamento do banco não permite se passar por
    ninguém. `substituido_por_id` encadeia a rotação, o que torna
    detectável o reuso de um token antigo — sinal de token roubado.
    """

    __tablename__ = "refresh_tokens"

    usuario_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    dispositivo_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE")
    )
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revogado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    substituido_por_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("refresh_tokens.id", ondelete="SET NULL")
    )
    ip: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("ix_refresh_tokens_usuario_validade", "usuario_id", "expira_em"),
    )


class Dispositivo(PKUUID, Timestamps, Base):
    __tablename__ = "devices"

    usuario_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    instalacao_id: Mapped[str] = mapped_column(String(128), nullable=False)
    plataforma: Mapped[Plataforma] = mapped_column(
        ENUM(Plataforma, name="plataforma", create_type=True), nullable=False
    )
    modelo: Mapped[str | None] = mapped_column(String(120))
    versao_android: Mapped[str | None] = mapped_column(String(30))
    versao_app: Mapped[str | None] = mapped_column(String(30))

    # O que este aparelho consegue fazer, respondido por ele na primeira
    # conexão. Evita a API pedir captura a um dispositivo sem permissão.
    pode_capturar: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pode_localizar: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pode_sobrepor: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    ultimo_acesso_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revogado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("usuario_id", "instalacao_id", name="instalacao_unica_por_usuario"),
    )
