# Rodar o projeto inteiro na sua máquina

Sem PostgreSQL, sem Docker, sem EasyPanel. Serve para desenvolver e para
ver a integração funcionando antes do deploy.

## 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

export DATABASE_URL="sqlite+aiosqlite:///./devlog-dev.db"
export JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export ENVIRONMENT=development
export CORS_ORIGINS="http://localhost:5173,http://127.0.0.1:5173"

python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.models import *
from app.db.base import Base
async def m():
    e = create_async_engine('sqlite+aiosqlite:///./devlog-dev.db')
    async with e.begin() as c: await c.run_sync(Base.metadata.create_all)
    await e.dispose()
asyncio.run(m())
"

uvicorn app.main:app --reload --port 8000
```

Documentação interativa em <http://127.0.0.1:8000/api/docs>.

**SQLite só vale em desenvolvimento.** A configuração recusa qualquer
banco que não seja PostgreSQL quando `ENVIRONMENT=production` — não dá
para subir em produção com SQLite por engano.

## 2. Front-end

```bash
cd frontend
npm install
VITE_API_URL=http://127.0.0.1:8000 npm run dev
```

Sem `VITE_API_URL`, o app roda em **modo local**: os dados ficam no
`localStorage`, exatamente como o site publicado hoje. É isso que
permite migrar sem apagão — enquanto o backend não estiver publicado
(Fase 7), o site continua no ar.

## 3. Testes

```bash
# backend — 155 testes, SQLite em memória
cd backend && pytest -q

# front-end — 40 cenários contra o build
cd frontend && npm run build
python3 -m http.server 4173 --directory dist &
npm test

# integração — cliente da API num navegador de verdade
# (exige backend e `npm run dev` no ar)
npm run test:integracao
npm run test:app-online     # fluxo completo pela interface
npm run test:recompensas    # trilhas, níveis, solicitar/confirmar entrega
npm run test:materias       # criar/renomear/arquivar matéria, refletido no objetivo
npm run test:progresso      # histórico recente na Home, com paginação
npm run test:adiantamento   # formulário + oferta de adiantar após concluir
```

O Playwright não está no `package.json` de propósito: instalá-lo faria o
workflow do Pages baixar ~150 MB de navegadores a cada build. Instale
com `npm i -g playwright` para rodar os testes de navegador.

## Armadilha que já custou tempo

Para o navegador, **`127.0.0.1` e `localhost` são origens diferentes**.
Autorizar só uma das duas em `CORS_ORIGINS` faz toda chamada falhar com
`Failed to fetch`, sem nenhuma pista no console. Por isso o exemplo
acima lista as duas.
