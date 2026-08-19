"""Base declarativa e convenções compartilhadas por todos os modelos."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Nomes previsíveis para índices e constraints. Sem isso, o Alembic gera
# nomes automáticos que variam entre versões e tornam impossível escrever
# uma migração de downgrade confiável.
CONVENCAO = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=CONVENCAO)


class PKUUID:
    """Chave primária UUID gerada na aplicação.

    UUID e não serial porque o Android cria registros offline e os envia
    depois: o cliente precisa saber o id antes de o servidor responder,
    senão não há como relacionar uma captura à sessão que a gerou
    enquanto o aparelho está sem rede.
    """

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)


class Timestamps:
    """Marcas de tempo em UTC, preenchidas pelo banco.

    `server_default=func.now()` em vez de default do Python: assim o
    horário é o do banco, único para todas as instâncias da API, e não o
    relógio de cada container.
    """

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
