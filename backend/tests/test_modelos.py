"""Testes do esquema — garantem que as regras estão no banco, e não só no código."""

from app.db.base import Base
from app.models import *  # noqa: F401,F403

TABELAS_ESPERADAS = {
    "users", "families", "family_members", "refresh_tokens", "devices",
    "subjects", "objectives", "objective_occurrences", "study_sessions",
    "session_events", "screen_captures", "known_locations", "session_locations",
    "point_ledger", "reward_tracks", "reward_levels", "reward_unlocks",
    "notifications", "audit_logs",
}


def test_todas_as_tabelas_da_especificacao_existem():
    assert set(Base.metadata.tables) == TABELAS_ESPERADAS


def test_ddl_do_postgres_compila():
    """Se os modelos gerarem DDL inválido, é aqui que se descobre."""
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.schema import CreateTable

    d = postgresql.dialect()
    for t in Base.metadata.sorted_tables:
        assert "CREATE TABLE" in str(CreateTable(t).compile(dialect=d))


def test_ocorrencia_nao_pode_duplicar_na_mesma_data():
    """A proteção que impede uma aula adiantada de reaparecer na data original."""
    t = Base.metadata.tables["objective_occurrences"]
    unicos = [
        {c.name for c in c_.columns}
        for c_ in t.constraints
        if type(c_).__name__ == "UniqueConstraint"
    ]
    assert {"objetivo_id", "prevista_para"} in unicos


def test_pontos_tem_chave_de_idempotencia():
    """Sem ela, reenviar a finalização de uma sessão creditaria em dobro."""
    coluna = Base.metadata.tables["point_ledger"].c.chave_idempotencia
    assert coluna.unique is True


def test_sessao_separa_tempo_verificado_do_nao_verificado():
    colunas = set(Base.metadata.tables["study_sessions"].c.keys())
    assert {"segundos_verificados", "segundos_nao_verificados"} <= colunas


def test_sessao_nao_aceita_tempo_negativo():
    # A convenção de nomes prefixa com ck_<tabela>_, o que torna os nomes
    # previsíveis entre versões do Alembic.
    checks = {
        c.name for c in Base.metadata.tables["study_sessions"].constraints
        if type(c).__name__ == "CheckConstraint"
    }
    assert "ck_study_sessions_brutos_nao_negativos" in checks
    assert "ck_study_sessions_validos_cabem_no_bruto" in checks


def test_convencao_de_nomes_vale_para_todas_as_constraints():
    """Nome automático varia entre versões e quebra o downgrade."""
    for nome, t in Base.metadata.tables.items():
        for c in t.constraints:
            if type(c).__name__ == "CheckConstraint":
                assert c.name.startswith(f"ck_{nome}_"), f"{nome}: {c.name}"


def test_membro_nao_se_repete_na_familia():
    t = Base.metadata.tables["family_members"]
    unicos = [
        {c.name for c in c_.columns}
        for c_ in t.constraints
        if type(c_).__name__ == "UniqueConstraint"
    ]
    assert {"familia_id", "usuario_id"} in unicos


def test_captura_guarda_caminho_e_nao_o_arquivo():
    """Imagem em bytea no PostgreSQL é proibido pela seção 17."""
    colunas = Base.metadata.tables["screen_captures"].c
    assert "caminho" in colunas
    assert not any(str(c.type).upper().startswith("BYTEA") for c in colunas)


def test_toda_tabela_tem_chave_primaria():
    for nome, t in Base.metadata.tables.items():
        assert len(t.primary_key.columns) >= 1, f"{nome} sem chave primária"
