"""Endpoints de autenticação.

O refresh token viaja em cookie HttpOnly, e não no corpo da resposta:
assim o JavaScript da página não consegue lê-lo, o que limita o estrago
de um XSS. O access token, de vida curta, fica na memória do front.
"""

from uuid import UUID

from fastapi import APIRouter, Request, Response, status

from app.api.deps import AdminDaFamilia, Sessao, UsuarioLogado
from app.core.config import get_settings
from app.core.exceptions import NaoAutenticado
from app.schemas.auth import (
    CadastroResponsavel,
    Credenciais,
    CriarDependente,
    RedefinirSenhaDependente,
    UsuarioPublico,
)
from app.schemas.auth import (
    Sessao as SessaoResposta,
)
from app.services import auth

router = APIRouter(prefix="/auth", tags=["autenticação"])

COOKIE_REFRESH = "devlog_refresh"


def _gravar_cookie(resposta: Response, refresh_claro: str) -> None:
    s = get_settings()
    resposta.set_cookie(
        key=COOKIE_REFRESH,
        value=refresh_claro,
        httponly=True,                       # fora do alcance do JavaScript
        secure=s.cookie_secure,
        samesite=s.COOKIE_SAMESITE,
        max_age=s.REFRESH_TOKEN_DAYS * 24 * 3600,
        path=f"{s.API_PREFIX}/auth",         # só é enviado para os endpoints de auth
    )


def _montar_resposta(aberta: auth.SessaoAberta) -> SessaoResposta:
    return SessaoResposta(
        access_token=aberta.access_token,
        expira_em_segundos=aberta.expira_em_segundos,
        usuario=UsuarioPublico.model_validate(aberta.usuario),
        familia_id=aberta.familia_id,
        papel=aberta.papel,
    )


@router.post("/cadastrar", response_model=SessaoResposta, status_code=status.HTTP_201_CREATED)
async def cadastrar(dados: CadastroResponsavel, resposta: Response, sessao: Sessao):
    """Cria responsável, família e vínculo de administrador."""
    aberta = await auth.cadastrar_responsavel(
        sessao,
        nome_exibicao=dados.nome_exibicao,
        username=dados.username,
        email=dados.email,
        senha=dados.senha,
        nome_familia=dados.nome_familia,
    )
    await sessao.commit()
    _gravar_cookie(resposta, aberta.refresh_claro)
    return _montar_resposta(aberta)


@router.post("/entrar", response_model=SessaoResposta)
async def entrar(dados: Credenciais, request: Request, resposta: Response, sessao: Sessao):
    aberta = await auth.entrar(
        sessao,
        identificador=dados.identificador,
        senha=dados.senha,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await sessao.commit()
    _gravar_cookie(resposta, aberta.refresh_claro)
    return _montar_resposta(aberta)


@router.post("/renovar", response_model=SessaoResposta)
async def renovar(request: Request, resposta: Response, sessao: Sessao):
    refresh = request.cookies.get(COOKIE_REFRESH)
    if not refresh:
        raise NaoAutenticado("Sessão não encontrada.")

    aberta = await auth.renovar(sessao, refresh_claro=refresh)
    await sessao.commit()
    _gravar_cookie(resposta, aberta.refresh_claro)
    return _montar_resposta(aberta)


@router.post("/sair", status_code=status.HTTP_204_NO_CONTENT)
async def sair(request: Request, resposta: Response, sessao: Sessao):
    refresh = request.cookies.get(COOKIE_REFRESH)
    if refresh:
        await auth.sair(sessao, refresh_claro=refresh)
        await sessao.commit()
    resposta.delete_cookie(COOKIE_REFRESH, path=f"{get_settings().API_PREFIX}/auth")


@router.post("/sair-de-todos", status_code=status.HTTP_204_NO_CONTENT)
async def sair_de_todos(usuario: UsuarioLogado, resposta: Response, sessao: Sessao):
    await auth.sair_de_todos(sessao, usuario_id=usuario.id)
    await sessao.commit()
    resposta.delete_cookie(COOKIE_REFRESH, path=f"{get_settings().API_PREFIX}/auth")


@router.get("/eu", response_model=UsuarioPublico)
async def eu(usuario: UsuarioLogado):
    return UsuarioPublico.model_validate(usuario)


@router.post(
    "/dependentes", response_model=UsuarioPublico, status_code=status.HTTP_201_CREATED
)
async def criar_dependente(
    dados: CriarDependente, usuario: UsuarioLogado, vinculo: AdminDaFamilia, sessao: Sessao
):
    """Só o responsável da família cria dependentes."""
    dependente = await auth.criar_dependente(
        sessao,
        responsavel=usuario,
        familia_id=vinculo.familia_id,
        nome_exibicao=dados.nome_exibicao,
        username=dados.username,
        email=dados.email,
        senha_temporaria=dados.senha_temporaria,
        parentesco=dados.parentesco,
    )
    await sessao.commit()
    return UsuarioPublico.model_validate(dependente)


@router.post(
    "/dependentes/{dependente_id}/redefinir-senha", status_code=status.HTTP_204_NO_CONTENT
)
async def redefinir_senha_dependente(
    dependente_id: UUID, dados: RedefinirSenhaDependente, vinculo: AdminDaFamilia, sessao: Sessao
):
    """Só o responsável troca a senha de um dependente — e nunca vê a atual."""
    await auth.redefinir_senha_dependente(
        sessao, familia_id=vinculo.familia_id, dependente_id=dependente_id,
        senha_nova=dados.senha_nova,
    )
    await sessao.commit()


@router.post("/dependentes/{dependente_id}/desativar", response_model=UsuarioPublico)
async def desativar_dependente(dependente_id: UUID, vinculo: AdminDaFamilia, sessao: Sessao):
    dependente = await auth.definir_ativo_dependente(
        sessao, familia_id=vinculo.familia_id, dependente_id=dependente_id, ativo=False,
    )
    await sessao.commit()
    return UsuarioPublico.model_validate(dependente)


@router.post("/dependentes/{dependente_id}/reativar", response_model=UsuarioPublico)
async def reativar_dependente(dependente_id: UUID, vinculo: AdminDaFamilia, sessao: Sessao):
    dependente = await auth.definir_ativo_dependente(
        sessao, familia_id=vinculo.familia_id, dependente_id=dependente_id, ativo=True,
    )
    await sessao.commit()
    return UsuarioPublico.model_validate(dependente)
