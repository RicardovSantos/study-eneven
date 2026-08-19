"""Acesso a dados de usuários, famílias e vínculos.

Camada fina de propósito: só consulta e grava. Regra de negócio fica nos
serviços — assim dá para testar a regra sem banco e trocar o banco sem
mexer na regra.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PapelFamiliar, StatusMembro
from app.models.identidade import Familia, MembroFamilia, Usuario


async def por_id(sessao: AsyncSession, usuario_id: UUID) -> Usuario | None:
    return await sessao.get(Usuario, usuario_id)


async def por_username(sessao: AsyncSession, username: str) -> Usuario | None:
    r = await sessao.execute(select(Usuario).where(Usuario.username == username.lower()))
    return r.scalar_one_or_none()


async def por_email(sessao: AsyncSession, email: str) -> Usuario | None:
    r = await sessao.execute(select(Usuario).where(Usuario.email == email.lower()))
    return r.scalar_one_or_none()


async def por_identificador(sessao: AsyncSession, identificador: str) -> Usuario | None:
    """Login aceita username ou e-mail no mesmo campo."""
    achado = await por_username(sessao, identificador)
    if achado is None and "@" in identificador:
        achado = await por_email(sessao, identificador)
    return achado


async def vinculo_ativo(sessao: AsyncSession, usuario_id: UUID) -> MembroFamilia | None:
    """Vínculo familiar ativo do usuário.

    É daqui que sai o papel usado em toda autorização. Nunca do que o
    cliente informa, nem do que está escrito no JWT.
    """
    r = await sessao.execute(
        select(MembroFamilia).where(
            MembroFamilia.usuario_id == usuario_id,
            MembroFamilia.status == StatusMembro.ATIVO,
        )
    )
    return r.scalars().first()


async def vinculo_na_familia(
    sessao: AsyncSession, usuario_id: UUID, familia_id: UUID
) -> MembroFamilia | None:
    r = await sessao.execute(
        select(MembroFamilia).where(
            MembroFamilia.usuario_id == usuario_id,
            MembroFamilia.familia_id == familia_id,
            MembroFamilia.status == StatusMembro.ATIVO,
        )
    )
    return r.scalar_one_or_none()


async def membros_da_familia(
    sessao: AsyncSession, familia_id: UUID, papel: PapelFamiliar | None = None
) -> list[MembroFamilia]:
    consulta = select(MembroFamilia).where(
        MembroFamilia.familia_id == familia_id,
        MembroFamilia.status == StatusMembro.ATIVO,
    )
    if papel is not None:
        consulta = consulta.where(MembroFamilia.papel == papel)
    r = await sessao.execute(consulta)
    return list(r.scalars())


async def criar_usuario(
    sessao: AsyncSession,
    *,
    username: str,
    email: str | None,
    senha_hash: str,
    nome_exibicao: str,
) -> Usuario:
    u = Usuario(
        username=username.lower(),
        email=email.lower() if email else None,
        senha_hash=senha_hash,
        nome_exibicao=nome_exibicao,
    )
    sessao.add(u)
    await sessao.flush()      # atribui o id sem confirmar a transação
    return u


async def criar_familia(sessao: AsyncSession, *, nome: str, dono_id: UUID) -> Familia:
    f = Familia(nome=nome, dono_id=dono_id)
    sessao.add(f)
    await sessao.flush()
    return f


async def criar_vinculo(
    sessao: AsyncSession,
    *,
    familia_id: UUID,
    usuario_id: UUID,
    papel: PapelFamiliar,
    parentesco: str | None = None,
    criado_por_id: UUID | None = None,
) -> MembroFamilia:
    v = MembroFamilia(
        familia_id=familia_id,
        usuario_id=usuario_id,
        papel=papel,
        parentesco=parentesco,
        criado_por_id=criado_por_id,
    )
    sessao.add(v)
    await sessao.flush()
    return v
