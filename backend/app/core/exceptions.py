"""Erros do domínio, com a resposta HTTP que cada um deve virar."""

from fastapi import HTTPException, status


class ErroDoDominio(HTTPException):
    pass


class CredenciaisInvalidas(ErroDoDominio):
    def __init__(self) -> None:
        # Mensagem propositalmente vaga: dizer "usuário não existe"
        # confirmaria para um atacante quais contas existem.
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha não conferem.",
            headers={"WWW-Authenticate": "Bearer"},
        )


class NaoAutenticado(ErroDoDominio):
    def __init__(self, detalhe: str = "É preciso entrar para continuar.") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detalhe,
            headers={"WWW-Authenticate": "Bearer"},
        )


class SemPermissao(ErroDoDominio):
    def __init__(self, detalhe: str = "Você não tem permissão para isso.") -> None:
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detalhe)


class JaExiste(ErroDoDominio):
    def __init__(self, detalhe: str) -> None:
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detalhe)


class NaoEncontrado(ErroDoDominio):
    def __init__(self, detalhe: str = "Não encontrado.") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detalhe)


class ContaDesativada(ErroDoDominio):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN, detail="Esta conta está desativada."
        )
