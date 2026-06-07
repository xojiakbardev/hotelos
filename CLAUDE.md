# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack & layout

- **Client**: Vue 3 + Vite + TS + Pinia + Vue Router + Tailwind + Radix-Vue (shadcn-style components in `client/src/components`). Axios for HTTP, native WebSocket for live updates.
- **Server**: Six Python 3.12 FastAPI services under `server/<name>-service/`, all sharing the same internal layout: `src/{api,core,domain,events,infra,services}`, plus `manage.py`, `alembic/`, `pyproject.toml`, `Dockerfile`.
- **Infra**: Postgres 16 (one schema per service, schemas bootstrapped from `infra/postgres/init/`), Redis 7 (Pub/Sub broker), Nginx reverse proxy. Everything runs via `docker-compose.yml`; production variant is `docker-compose.prod.yml`.

## Architecture

Nginx is the only public entrypoint (host port **8080**). It routes `/api/<service>/...` to the matching FastAPI upstream and `/ws` to `ws-gateway`. **Services never call each other over HTTP** — they communicate only through Redis Pub/Sub. Each service owns its Postgres schema; cross-schema reads are forbidden, so projections (e.g. `room-service` mirroring kitchen-relevant orders) are built by subscribing to events.

`ws-gateway` subscribes to all relevant Redis channels and fans events out to connected dashboards with **role-aware redaction**. The Vue client updates **optimistically** on user actions; the authoritative confirmation arrives via WebSocket and reconciles the optimistic state.

Event channel names double as the `event` field in the envelope (see `server/<svc>/src/events/topics.py`). Prefixes matter — `ws-gateway` pattern-matches on them (`rooms.*`, `orders.*`, `guests.*`, …). When adding an event, add it to `topics.py` on the publishing service and to the subscriber's `events/handlers.py` on consuming services.

## Commands

All commands run via `docker compose exec <service> ...`. The Python services use a Django-style `manage.py` (Click + Alembic + SQLAlchemy async):

```bash
docker compose up --build                                              # first run
docker compose exec auth-service python manage.py seedusers            # demo users (one per role)
docker compose exec auth-service python manage.py createmanager        # interactive single-manager
docker compose exec <svc> python manage.py makemigrations "<message>"  # autogen revision
docker compose exec <svc> python manage.py migrate                     # alembic upgrade head
docker compose exec <svc> pytest                                       # tests (when present)
docker compose logs -f <svc>
docker compose down -v                                                 # nuke DB + reset
```

Client (run inside `client/`, or use the container):

```bash
npm run dev      # vite dev server
npm run build    # vue-tsc -b && vite build
npm run lint     # eslint . --ext .ts,.vue
npm run format   # prettier
```

Run a single backend test: `docker compose exec <svc> pytest path/to/test_x.py::test_name -xvs`.

## Conventions specific to this repo

- **Identity is phone-based**, not email. Login uses `+998...` phone numbers (see demo credentials in README). The `auth-service` issues JWTs and owns RBAC.
- **Four staff roles** (`manager`, `reception`, `technician`, `cleaner`) plus a `kitchen` role for the room-service projection. There is no super_admin. Reception owns the room-service order lifecycle from intake to delivery.
- **Dependency injection**: plain FastAPI `Depends` — no Dishka, no other DI framework.
- **Hot reload is on**: each service mounts its `src/` and `alembic/` as bind mounts and runs `uvicorn --reload`. Editing files on the host immediately reloads inside the container; no rebuild needed for code changes. **Rebuild only when `pyproject.toml` or `Dockerfile` changes.**
- **DNS caching gotcha**: after `docker compose up --build` of any backend service, Nginx may keep routing to the old container IP. Restart nginx (`docker compose restart nginx`) when a service was rebuilt.
- **UI**: resource-based routes (list/detail/create/edit + action routes); avoid cramming form + table + edit into one page. All user-facing text is in **Uzbek**.

## Where to look

- Event catalog & cross-service contracts: `docs/events.md` (referenced by README; create if missing before adding new events).
- Per-service routers: `server/<svc>/src/api/routers/` — one file per resource.
- Pinia stores mirror service boundaries: `client/src/stores/{guests,rooms,orders,housekeeping,maintenance,staff,ws}.ts`.
- WebSocket client + event dispatch: `client/src/stores/ws.ts`.
