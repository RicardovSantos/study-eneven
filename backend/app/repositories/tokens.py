"""Refresh tokens: emissão, consulta, rotação e revogação."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.identidade import RefreshToken


async def guardar(
    sessao: AsyncSession,
    *,
    usuario_id: UUID,
    token_hash: str,
    dias: int,
    dispositivo_id: UUID | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> RefreshToken:
    t = RefreshToken(
        usuario_id=usuario_id,
        token_hash=token_hash,
        dispositivo_id=dispositivo_id,
        expira_em=datetime.now(UTC) + timedelta(days=dias),
        ip=ip,
        user_agent=user_agent,
    )
    sessao.add(t)
    await sessao.flush()
    return t


async def por_hash(sessao: AsyncSession, token_hash: str) -> RefreshToken | None:
    r = await sessao.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    return r.scalar_one_or_none()


def esta_valido(t: RefreshToken | None) -> bool:
    if t is None or t.revogado_em is not None:
        return False
    expira = t.expira_em
    if expira.tzinfo is None:          # SQLite devolve datetime sem fuso
        expira = expira.replace(tzinfo=UTC)
    return expira > datetime.now(UTC)


async def revogar(sessao: AsyncSession, t: RefreshToken, substituido_por_id: UUID | None = None):
    t.revogado_em = datetime.now(UTC)
    t.substituido_por_id = substituido_por_id
    await sessao.flush()


async def revogar_todos_do_usuario(sessao: AsyncSession, usuario_id: UUID) -> int:
    """Sair de todos os aparelhos.

    Também é o que se faz ao detectar reuso de token: se um refresh já
    rotacionado voltar a aparecer, ele provavelmente foi roubado, e a
    resposta segura é derrubar a cadeia inteira.
    """
    r = await sessao.execute(
        update(RefreshToken)
        .where(RefreshToken.usuario_id == usuario_id, RefreshToken.revogado_em.is_(None))
        .values(revogado_em=datetime.now(UTC))
    )
    await sessao.flush()
    return r.rowcount or 0
