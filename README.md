# HotelOS

Real-time hotel management system for the GrandStay Hotel staff. Built for the BTEC HND Level 4 *Module 4: Programming* assignment. See `docs/` for the full architecture, event catalog, and decisions log; see `CLAUDE.md` for working conventions.

## Stack at a glance

| Layer | Technology |
|---|---|
| Client | Vue 3 + Vite + TypeScript + Pinia + Vue Router |
| Backend | Python 3.12 + FastAPI per service, SQLAlchemy 2.0 async, Alembic, Click `manage.py` |
| Broker | Redis Pub/Sub |
| Real-time | `ws-gateway` (FastAPI WebSocket fan-out) |
| Database | PostgreSQL 16, one schema per service |
| Edge | Nginx reverse proxy |
| Orchestration | Docker Compose |

## Services

| Service | Port (internal) | Schema | Role |
|---|---|---|---|
| `auth-service` | 8000 | `auth` | JWT login, RBAC, staff CRUD |
| `reception-service` | 8000 | `reception` | Guests, check-in/out, billing, room service order lifecycle |
| `housekeeping-service` | 8000 | `housekeeping` | Cleaning queue, room cleanliness |
| `room-service` | 8000 | `room_service` | Kitchen-side order projection |
| `maintenance-service` | 8000 | `maintenance` | Priority queue, technician assignment |
| `ws-gateway` | 8000 | — | Subscribes to Redis, fans out to connected dashboards |
| `client` | 80 | — | Vue dashboard (Vite dev) |
| `nginx` | 80 → host **8080** | — | Reverse proxy + WS upgrade |

Public URL once running: **http://localhost:8080**

## Prerequisites

- Docker 24+ with Compose v2
- 4 GB free RAM
- Ports 8080, 5432, 6379 free on the host

## First run

```bash
cp .env.example .env
docker compose up --build
```

Watch the logs until you see `Uvicorn running on 0.0.0.0:8000` for every service and `nginx` listening on port 80.

In another terminal, seed demo users (one per role):

```bash
docker compose exec auth-service python manage.py seedusers
```

Or create a single manager interactively:

```bash
docker compose exec auth-service python manage.py createmanager
```

Open **http://localhost:8080** and log in with one of the demo credentials below.

## Demo credentials

| Role | Phone | Password |
|---|---|---|
| Manager | `+998901111111` | `manager123` |
| Reception | `+998902222222` | `reception123` |
| Technician | `+998903333333` | `technician123` |
| Cleaner | `+998904444444` | `cleaner123` |
| Kitchen | `+998905555555` | `kitchen123` |

> Defined in `.env`. Change them before showing the system to anyone outside the assessor.

## Common operations

```bash
# View one service's logs
docker compose logs -f reception-service

# Seed demo users (run after first `docker compose up`)
docker compose exec auth-service python manage.py seedusers

# Create a single manager interactively
docker compose exec auth-service python manage.py createmanager

# Generate a new migration for one service
docker compose exec reception-service python manage.py makemigrations "add rooms table"

# Apply migrations
docker compose exec reception-service python manage.py migrate

# Run tests inside a service (once tests exist)
docker compose exec auth-service pytest

# Tear everything down (including volumes — resets DB)
docker compose down -v

# Full rebuild from scratch (clean start)
docker compose down -v --rmi local
docker compose up --build -d
docker compose exec auth-service python manage.py seedusers
```

## Project layout

```
hotelos/
├── client/                 # Vue 3 dashboard
├── server/
│   ├── auth-service/       # JWT, users, manage.py createmanager / seedusers
│   ├── reception-service/  # check-in, check-out, billing, orders
│   ├── housekeeping-service/
│   ├── room-service/       # kitchen-side projection
│   ├── maintenance-service/
│   └── ws-gateway/         # Redis → WebSocket fan-out
├── nginx/                  # reverse proxy config
├── infra/postgres/init/    # bootstrap schemas on first DB start
├── design-system/          # design tokens (MASTER + per-page overrides)
├── docs/                   # decisions, architecture diagrams, event catalog
├── docker-compose.yml
├── .env.example
└── CLAUDE.md               # contributor / future-Claude-session guide
```

## Architecture in one paragraph

A Vue dashboard talks to **Nginx**. Nginx splits traffic to the right FastAPI service (`/api/<service>/...`) or to `ws-gateway` (`/ws`). FastAPI services own their own Postgres **schema** and never call each other. When something interesting happens, a service publishes a **Redis Pub/Sub** event. Other services that care subscribe; `ws-gateway` subscribes to everything and fans out to connected dashboards with role-aware redaction. The dashboard updates **optimistically** the moment the user clicks; server-pushed events confirm or correct the optimistic state.

For diagrams, see [`docs/architecture.md`](docs/architecture.md). For the event catalog, [`docs/events.md`](docs/events.md). For decision rationale, [`docs/decisions.md`](docs/decisions.md).

## License

This is an academic project. Do not redistribute without permission.
