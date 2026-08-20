"""Regras de autenticação.

O que este módulo garante, e que a versão em localStorage não garantia:

- senha nunca é guardada nem comparada em texto puro;
- o papel de alguém vem do vínculo familiar no banco, nunca do cliente;
- refresh token é rotativo: usar um gera outro e invalida o anterior;
- reuso de token já rotacionado derruba todas as sessões do usuário.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import (
    ContaDesativada,
    CredenciaisInvalidas,
    JaExiste,
    NaoAutenticado,
    NaoEncontrado,
    SemPermissao,
)
from app.core.security import (
    conferir_senha,
    criar_access_token,
    gerar_hash_senha,
    gerar_refresh_token,
    hash_refresh_token,
)
from app.models.enums import PapelFamiliar
from app.models.identidade import Usuario
from app.repositories import tokens as repo_tokens
from app.repositories import usuarios as repo


@dataclass
class SessaoAberta:
    usuario: Usuario
    familia_id: UUID | None
    papel: str | None
    access_token: str
    refresh_claro: str
    expira_em_segundos: int


async def _abrir_sessao(
    sessao: AsyncSession, usuario: Usuario, ip: str | None = None, user_agent: str | None = None
) -> SessaoAberta:
    s = get_settings()
    vinculo = await repo.vinculo_ativo(sessao, usuario.id)
    familia_id = vinculo.familia_id if vinculo else None
    papel = vinculo.papel.value if vinculo else None

    claro, hash_token = gerar_refresh_token()
    await repo_tokens.guardar(
        sessao,
        usuario_id=usuario.id,
        token_hash=hash_token,
        dias=s.REFRESH_TOKEN_DAYS,
        ip=ip,
        user_agent=user_agent,
    )
    return SessaoAberta(
        usuario=usuario,
        familia_id=familia_id,
        papel=papel,
        access_token=criar_access_token(usuario.id, familia_id, papel),
        refresh_claro=claro,
        expira_em_segundos=s.ACCESS_TOKEN_MINUTES * 60,
    )


async def cadastrar_responsavel(
    sessao: AsyncSession,
    *,
    nome_exibicao: str,
    username: str,
    email: str,
    senha: str,
    nome_familia: str,
) -> SessaoAberta:
    """Cria o usuário, a família e o vínculo de administrador numa transação."""
    if await repo.por_username(sessao, username):
        raise JaExiste("Este nome de usuário já está em uso.")
    if await repo.por_email(sessao, email):
        raise JaExiste("Já existe uma conta com este e-mail.")

    usuario = await repo.criar_usuario(
        sessao,
        username=username,
        email=email,
        senha_hash=gerar_hash_senha(senha),
        nome_exibicao=nome_exibicao,
    )
    familia = await repo.criar_familia(sessao, nome=nome_familia, dono_id=usuario.id)
    await repo.criar_vinculo(
        sessao, familia_id=familia.id, usuario_id=usuario.id, papel=PapelFamiliar.ADMIN
    )
    return await _abrir_sessao(sessao, usuario)


async def criar_dependente(
    sessao: AsyncSession,
    *,
    responsavel: Usuario,
    familia_id: UUID,
    nome_exibicao: str,
    username: str,
    email: str | None,
    senha_temporaria: str,
    parentesco: str | None = None,
) -> Usuario:
    """Só um administrador da própria família pode criar dependente."""
    vinculo = await repo.vinculo_na_familia(sessao, responsavel.id, familia_id)
    if vinculo is None or vinculo.papel != PapelFamiliar.ADMIN:
        raise SemPermissao("Apenas o responsável da família pode criar contas.")

    if await repo.por_username(sessao, username):
        raise JaExiste("Este nome de usuário já está em uso.")
    if email and await repo.por_email(sessao, email):
        raise JaExiste("Já existe uma conta com este e-mail.")

    dependente = await repo.criar_usuario(
        sessao,
        username=username,
        email=email,
        senha_hash=gerar_hash_senha(senha_temporaria),
        nome_exibicao=nome_exibicao,
    )
    await repo.criar_vinculo(
        sessao,
        familia_id=familia_id,
        usuario_id=dependente.id,
        papel=PapelFamiliar.DEPENDENTE,
        parentesco=parentesco,
        criado_por_id=responsavel.id,
    )
    return dependente


async def _exigir_dependente_da_familia(
    sessao: AsyncSession, *, familia_id: UUID, dependente_id: UUID
) -> Usuario:
    """Confere que o alvo é mesmo um dependente desta família — sem
    isso, o id de outra família (ou do próprio responsável) passaria.
    404 e não 403: um 403 confirmaria que o id existe em outro lugar."""
    vinculo_dep = await repo.vinculo_na_familia(sessao, dependente_id, familia_id)
    if vinculo_dep is None or vinculo_dep.papel != PapelFamiliar.DEPENDENTE:
        raise NaoEncontrado("Dependente não encontrado.")
    dependente = await repo.por_id(sessao, dependente_id)
    if dependente is None:
        raise NaoEncontrado("Dependente não encontrado.")
    return dependente


async def redefinir_senha_dependente(
    sessao: AsyncSession, *, familia_id: UUID, dependente_id: UUID, senha_nova: str
) -> None:
    """O responsável nunca vê a senha atual — só define uma nova.

    Derruba as sessões abertas do dependente: se o motivo da troca foi
    perder o controle da conta, deixar sessões antigas valendo anularia
    o propósito.
    """
    dependente = await _exigir_dependente_da_familia(
        sessao, familia_id=familia_id, dependente_id=dependente_id
    )
    dependente.senha_hash = gerar_hash_senha(senha_nova)
    await sair_de_todos(sessao, usuario_id=dependente.id)


async def definir_ativo_dependente(
    sessao: AsyncSession, *, familia_id: UUID, dependente_id: UUID, ativo: bool
) -> Usuario:
    """Desativar derruba as sessões abertas — `entrar()` já recusa
    conta inativa (ContaDesativada), mas um token ainda válido em
    memória continuaria autenticando até expirar sem isso."""
    dependente = await _exigir_dependente_da_familia(
        sessao, familia_id=familia_id, dependente_id=dependente_id
    )
    dependente.ativo = ativo
    if not ativo:
        await sair_de_todos(sessao, usuario_id=dependente.id)
    return dependente


async def entrar(
    sessao: AsyncSession,
    *,
    identificador: str,
    senha: str,
    ip: str | None = None,
    user_agent: str | None = None,
) -> SessaoAberta:
    usuario = await repo.por_identificador(sessao, identificador)

    # Confere a senha mesmo com usuário inexistente, contra um hash
    # descartável: sem isso, o tempo de resposta revelaria quais contas
    # existem (o caminho "não achei" retornaria bem mais rápido).
    if usuario is None:
        conferir_senha(senha, gerar_hash_senha("descartavel"))
        raise CredenciaisInvalidas
    if not conferir_senha(senha, usuario.senha_hash):
        raise CredenciaisInvalidas
    if not usuario.ativo:
        raise ContaDesativada

    return await _abrir_sessao(sessao, usuario, ip=ip, user_agent=user_agent)


async def renovar(sessao: AsyncSession, *, refresh_claro: str) -> SessaoAberta:
    """Troca um refresh token por um par novo.

    O antigo é revogado no mesmo passo. Se alguém tentar usar de novo um
    token já revogado, isso indica cópia roubada — e a resposta é derrubar
    todas as sessões daquele usuário, não só recusar a chamada.
    """
    guardado = await repo_tokens.por_hash(sessao, hash_refresh_token(refresh_claro))

    if guardado is not None and guardado.revogado_em is not None:
        await repo_tokens.revogar_todos_do_usuario(sessao, guardado.usuario_id)
        raise NaoAutenticado("Sessão encerrada por segurança. Entre novamente.")

    if not repo_tokens.esta_valido(guardado):
        raise NaoAutenticado("Sessão expirada. Entre novamente.")

    assert guardado is not None
    usuario = await repo.por_id(sessao, guardado.usuario_id)
    if usuario is None or not usuario.ativo:
        raise NaoAutenticado()

    nova = await _abrir_sessao(sessao, usuario)
    novo_registro = await repo_tokens.por_hash(sessao, hash_refresh_token(nova.refresh_claro))
    await repo_tokens.revogar(
        sessao, guardado, substituido_por_id=novo_registro.id if novo_registro else None
    )
    return nova


async def sair(sessao: AsyncSession, *, refresh_claro: str) -> None:
    guardado = await repo_tokens.por_hash(sessao, hash_refresh_token(refresh_claro))
    if guardado is not None and guardado.revogado_em is None:
        await repo_tokens.revogar(sessao, guardado)


async def sair_de_todos(sessao: AsyncSession, *, usuario_id: UUID) -> int:
    return await repo_tokens.revogar_todos_do_usuario(sessao, usuario_id)
