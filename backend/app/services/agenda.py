"""Geração das ocorrências a partir da regra do objetivo.

Um objetivo diz "inglês, 40 minutos, de segunda a sexta". Isso não é uma
obrigação — é a receita. As obrigações concretas ("aula do dia 21/08")
são as ocorrências, geradas por aqui.

A geração é **idempotente**: rodar duas vezes para o mesmo período não
duplica nada. Além da verificação em memória, o banco tem a restrição
única (objetivo_id, prevista_para) como última linha de defesa — duas
requisições simultâneas não conseguem criar a mesma obrigação.
"""

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Frequencia, StatusObjetivo, StatusOcorrencia
from app.models.objetivos import Objetivo, Ocorrencia

# Quanto à frente a agenda é materializada. Gerar o ano inteiro encheria
# a tabela de linhas que ninguém vai olhar; duas semanas cobrem a tela de
# hoje e o adiantamento de amanhã com folga.
JANELA_PADRAO_DIAS = 14


def _domingo_da(d: date) -> date:
    """Domingo da semana de `d` — o app trata a semana como dom→sáb."""
    return d - timedelta(days=(d.weekday() + 1) % 7)


def _primeiro_do_mes(d: date) -> date:
    return d.replace(day=1)


def datas_previstas(objetivo: Objetivo, de: date, ate: date) -> list[date]:
    """Datas em que este objetivo gera obrigação, no intervalo dado.

    Semanal e mensal ancoram no início do período (domingo, dia 1): assim
    a ocorrência é uma só por período, e não uma por dia.
    """
    if objetivo.inicia_em and de < objetivo.inicia_em:
        de = objetivo.inicia_em
    if objetivo.prazo_final and ate > objetivo.prazo_final:
        ate = objetivo.prazo_final
    if de > ate:
        return []

    dias: list[date] = []
    atual = de
    while atual <= ate:
        if objetivo.frequencia == Frequencia.DIARIA:
            # dias_semana usa 0=domingo, como o resto do app
            permitidos = objetivo.dias_semana
            if not permitidos or ((atual.weekday() + 1) % 7) in permitidos:
                dias.append(atual)
        elif objetivo.frequencia == Frequencia.SEMANAL:
            inicio = _domingo_da(atual)
            if inicio >= de and inicio not in dias:
                dias.append(inicio)
            elif inicio < de and de not in dias and not dias:
                # a semana já começou antes da janela: ancora no primeiro
                # dia visível, senão o período ficaria sem obrigação
                dias.append(de)
        elif objetivo.frequencia == Frequencia.MENSAL:
            inicio = _primeiro_do_mes(atual)
            alvo = inicio if inicio >= de else de
            if alvo not in dias:
                dias.append(alvo)
        else:
            # PERSONALIZADA usa exclusivamente dias_semana
            if objetivo.dias_semana and ((atual.weekday() + 1) % 7) in objetivo.dias_semana:
                dias.append(atual)
        atual += timedelta(days=1)
    return dias


async def gerar_para_objetivo(
    sessao: AsyncSession, objetivo: Objetivo, ate: date | None = None, hoje: date | None = None
) -> list[Ocorrencia]:
    """Cria as ocorrências que faltam até `ate`. Devolve só as novas."""
    if objetivo.status in (StatusObjetivo.ARQUIVADO, StatusObjetivo.CONCLUIDO,
                           StatusObjetivo.PAUSADO):
        return []

    hoje = hoje or date.today()
    ate = ate or (hoje + timedelta(days=JANELA_PADRAO_DIAS))

    previstas = datas_previstas(objetivo, hoje, ate)
    if not previstas:
        return []

    r = await sessao.execute(
        select(Ocorrencia.prevista_para).where(
            Ocorrencia.objetivo_id == objetivo.id,
            Ocorrencia.prevista_para.in_(previstas),
        )
    )
    existentes = {linha[0] for linha in r}

    novas = [
        Ocorrencia(
            objetivo_id=objetivo.id,
            titular_id=objetivo.titular_id,
            prevista_para=d,
            meta=objetivo.meta_periodo,
        )
        for d in previstas
        if d not in existentes
    ]
    sessao.add_all(novas)
    await sessao.flush()
    return novas


async def gerar_para_titular(
    sessao: AsyncSession, titular_id: UUID, ate: date | None = None, hoje: date | None = None
) -> int:
    """Materializa a agenda de todos os objetivos ativos de alguém."""
    r = await sessao.execute(
        select(Objetivo).where(
            Objetivo.titular_id == titular_id,
            Objetivo.status == StatusObjetivo.ANDAMENTO,
        )
    )
    total = 0
    for objetivo in r.scalars():
        total += len(await gerar_para_objetivo(sessao, objetivo, ate=ate, hoje=hoje))
    return total


async def marcar_perdidas(
    sessao: AsyncSession, titular_id: UUID, hoje: date | None = None
) -> int:
    """Fecha o que ficou para trás.

    Uma ocorrência pendente de ontem não some: vira `perdida`. É isso que
    permite mostrar "atrasadas" no painel e calcular a pendência
    acumulada com honestidade, em vez de fingir que o dia não existiu.
    """
    hoje = hoje or date.today()
    r = await sessao.execute(
        select(Ocorrencia).where(
            Ocorrencia.titular_id == titular_id,
            Ocorrencia.status == StatusOcorrencia.PENDENTE,
            Ocorrencia.prevista_para < hoje,
        )
    )
    perdidas = list(r.scalars())
    for o in perdidas:
        o.status = StatusOcorrencia.PERDIDA
    await sessao.flush()
    return len(perdidas)
