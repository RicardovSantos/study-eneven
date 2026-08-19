"""Dependências compartilhadas pelos endpoints."""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NaoAutenticado, SemPermissao
from app.core.security import ler_access_token
from app.db.session import get_sessao
from app.models.enums import PapelFamiliar
from app.models.identidade import MembroFamilia, Usuario
from app.repositories import usuarios as repo

Sessao = Annotated[AsyncSession, Depends(get_sessao)]


async def usuario_atual(request: Request, sessao: Sessao) -> Usuario:
    cabecalho = request.headers.get("Authorization", "")
    if not cabecalho.startswith("Bearer "):
        raise NaoAutenticado()

    corpo = ler_access_token(cabecalho.removeprefix("Bearer ").strip())
    if corpo is None:
        raise NaoAutenticado("Sessão inválida ou expirada.")

    from uuid import UUID
    try:
        usuario_id = UUID(corpo["sub"])
    except (KeyError, ValueError):
        raise NaoAutenticado() from None

    usuario = await repo.por_id(sessao, usuario_id)
    if usuario is None or not usuario.ativo:
        raise NaoAutenticado()
    return usuario


UsuarioLogado = Annotated[Usuario, Depends(usuario_atual)]


async def vinculo_atual(usuario: UsuarioLogado, sessao: Sessao) -> MembroFamilia:
    """Vínculo familiar lido do banco.

    Existe justamente para NÃO usar o `papel` que vem no JWT. O token
    pode ter sido emitido antes de o responsável mudar o papel de alguém;
    o banco é a única fonte de verdade para autorizar (seção 7.3).
    """
    vinculo = await repo.vinculo_ativo(sessao, usuario.id)
    if vinculo is None:
        raise SemPermissao("Sua conta não está vinculada a nenhuma família.")
    return vinculo


VinculoAtual = Annotated[MembroFamilia, Depends(vinculo_atual)]


async def exigir_admin(vinculo: VinculoAtual) -> MembroFamilia:
    if vinculo.papel != PapelFamiliar.ADMIN:
        raise SemPermissao("Esta área é só do responsável da família.")
    return vinculo


AdminDaFamilia = Annotated[MembroFamilia, Depends(exigir_admin)]
