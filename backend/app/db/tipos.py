"""Tipos que mudam conforme o banco.

O PostgreSQL recebe os tipos nativos (JSONB, INET). Qualquer outro banco
recebe um equivalente portátil — o que permite rodar a suíte de testes
contra SQLite em memória, sem precisar de um servidor no ambiente de
desenvolvimento nem na CI.

O DDL gerado para o PostgreSQL é idêntico ao que seria sem esta camada;
`with_variant` só acrescenta uma alternativa para os outros dialetos.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

JSONB_PORTATIL = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

# 45 caracteres cobrem um IPv6 completo com zona.
INET_PORTATIL = sa.String(45).with_variant(postgresql.INET(), "postgresql")
