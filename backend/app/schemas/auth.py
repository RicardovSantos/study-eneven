"""Contratos de entrada e saída da autenticação.

Separados dos modelos SQLAlchemy de propósito: o que o cliente envia e
recebe não é o que o banco guarda. `senha_hash`, por exemplo, nunca sai
daqui.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class CadastroResponsavel(BaseModel):
    nome_exibicao: str = Field(min_length=2, max_length=120)
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    senha: str = Field(min_length=8, max_length=128)
    nome_familia: str = Field(min_length=2, max_length=120)

    @field_validator("username")
    @classmethod
    def _username_simples(cls, v: str) -> str:
        limpo = v.strip().lower()
        if not limpo.replace("_", "").replace(".", "").isalnum():
            raise ValueError("use apenas letras, números, ponto e sublinhado")
        return limpo

    @field_validator("senha")
    @classmethod
    def _senha_com_alguma_forca(cls, v: str) -> str:
        # Mínimo honesto: 8 caracteres com letra e número. Regras muito
        # rígidas empurram para senhas anotadas em papel.
        if v.isdigit() or v.isalpha():
            raise ValueError("misture letras e números")
        return v


class CriarDependente(BaseModel):
    """Conta criada pelo responsável. E-mail é opcional."""

    nome_exibicao: str = Field(min_length=2, max_length=120)
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr | None = None
    senha_temporaria: str = Field(min_length=8, max_length=128)
    parentesco: str | None = Field(default=None, max_length=60)

    @field_validator("username")
    @classmethod
    def _minusculo(cls, v: str) -> str:
        return v.strip().lower()


class RedefinirSenhaDependente(BaseModel):
    """O responsável define uma nova senha — nunca vê a atual."""

    senha_nova: str = Field(min_length=8, max_length=128)

    @field_validator("senha_nova")
    @classmethod
    def _senha_com_alguma_forca(cls, v: str) -> str:
        if v.isdigit() or v.isalpha():
            raise ValueError("misture letras e números")
        return v


class EditarPerfil(BaseModel):
    """A própria pessoa edita os próprios dados. Trocar a senha exige
    confirmar a atual — sem isso, um token esquecido aberto em outro
    aparelho poderia trocar a senha sem a pessoa perceber."""

    nome_exibicao: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = None
    senha_atual: str | None = Field(default=None, min_length=1, max_length=128)
    senha_nova: str | None = Field(default=None, min_length=8, max_length=128)

    @field_validator("senha_nova")
    @classmethod
    def _senha_com_alguma_forca(cls, v: str | None) -> str | None:
        if v is not None and (v.isdigit() or v.isalpha()):
            raise ValueError("misture letras e números")
        return v

    @model_validator(mode="after")
    def _senha_nova_exige_atual(self):
        if self.senha_nova and not self.senha_atual:
            raise ValueError("informe a senha atual para trocar a senha")
        return self


class Credenciais(BaseModel):
    """Aceita username ou e-mail no mesmo campo."""

    identificador: str = Field(min_length=3, max_length=255)
    senha: str = Field(min_length=1, max_length=128)


class UsuarioPublico(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str | None
    nome_exibicao: str
    avatar_caminho: str | None
    ativo: bool
    criado_em: datetime


class Sessao(BaseModel):
    """Resposta do login.

    O refresh token não aparece aqui: ele vai em cookie HttpOnly, fora do
    alcance do JavaScript. Devolvê-lo no corpo obrigaria o front a
    guardá-lo em algum lugar que scripts leem.
    """

    access_token: str
    token_type: str = "bearer"
    expira_em_segundos: int
    usuario: UsuarioPublico
    familia_id: UUID | None = None
    papel: str | None = None
