# AI-Trading-Agent

A fleet of AI trading agents on a simulated real-time market. The goal is to analyse profits and
losses and find out whether LLM agents can beat simple strategies on the CAC 40.

> Work in progress: this README grows with each development phase.

## What if a team of AI agents managed your portfolio? Could they beat the CAC 40?

LLM agents read the charts, forecast where French stocks are heading, and trade them in real
time on live market data, with a simulated portfolio. Their results are compared with simple
strategies, using real trading fees.

- **Live mode:** during Euronext trading hours, the agents analyse the market every 15 to 30
  minutes and place orders that are executed by a simulated broker.
- **Replay mode:** past months are replayed day by day to measure performance quickly, using
  only the data available at each simulated moment.

## Tech stack

- **Backend:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL 16
- **Agents:** LangGraph with local LLMs served by Ollama (free), optional free-tier APIs
- **Tooling:** uv, ruff, mypy (strict), pytest, GitHub Actions, Docker Compose

## Project structure

```
backend/
├── app/
│   ├── main.py         # FastAPI application
│   ├── config.py       # settings read from .env
│   ├── database.py     # PostgreSQL connection and base table class
│   ├── models.py       # database tables
│   ├── routers/        # HTTP endpoints
│   ├── schemas/        # Pydantic schemas (API inputs and outputs)
│   └── services/       # business logic
├── alembic/            # database migrations
└── tests/
    ├── unit/           # fast, no database, no network
    └── integration/    # real PostgreSQL, migrations applied from scratch
```

Routers only handle HTTP and delegate to services, which hold the business logic.
Files are split into sub-modules only when they grow.

## Getting started

Prerequisites: [uv](https://docs.astral.sh/uv/), Docker, and GNU Make.

```bash
cp .env.example .env
make install      # backend dependencies
make db-up        # PostgreSQL in Docker
make migrate      # apply database migrations
make run          # API on http://localhost:8000
```

- Health check: `curl http://localhost:8000/api/v1/health`
- Interactive API docs: http://localhost:8000/docs

## Development

| Command | Description |
|---|---|
| `make test` | Unit tests |
| `make test-int` | Integration tests (PostgreSQL) |
| `make test-all` | All tests with coverage |
| `make lint` / `make format` | Check / fix code style |
| `make typecheck` | Static type checking |
| `make migration m="..."` | Generate a database migration from the models |

## Disclaimer

This project is a research and technical showcase. It is not investment advice, and no real
orders are ever sent to any market.

## License

[MIT](LICENSE)
