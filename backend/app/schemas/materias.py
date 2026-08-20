"""Contratos de matérias."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CriarMateria(BaseModel):
    nome: str = Field(min_length=1, max_length=80)
    cor: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    icone: str | None = Field(default=None, max_length=40)


class EditarMateria(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=80)
    cor: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    icone: str | None = Field(default=None, max_length=40)
    ativo: bool | None = None


class MateriaPublica(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    familia_id: UUID
    nome: str
    cor: str | None
    icone: str | None
    ativo: bool
