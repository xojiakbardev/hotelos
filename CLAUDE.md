# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project context

HotelOS is a **BTEC HND Level 4 academic assignment** (Module 4: Programming, H/618/7388, 15 credits) — a real-time hotel management system for the fictional GrandStay Hotel. Graded against a Pass/Merit/Distinction rubric covering four learning outcomes (LO1–LO4). Architecture matters; production polish and scale do not. **2 floors × 10 rooms is sufficient** — do not scale to 120 rooms.

The assignment requires three mandatory architectural technologies, each in a working (not enterprise-complete) form:

1. **Microservices** — at least four independently runnable services that never call each other directly.
2. **Message broker** — publish/subscribe communication between services.
3. **WebSocket** — live updates to the operations dashboard without page refresh.

## Tech stack (decided)

- **Client:** Vue 3 + Vite (TypeScript), Pinia for state, Vue Router 4. Lives in `client/`.
- **Backend services:** Python 3.12 + FastAPI. Each service is its own folder under `server/`.
- **DI:** FastAPI's built-in `Depends()`. **Do not use Dishka** — explicitly removed.
- **ORM:** SQLAlchemy 2.0 async with `AsyncSession`.
- **Migrations:** Alembic, scoped per service to its own schema.
- **CLI:** Click — each service has a Django-style `manage.py` (see CLI section below).
- **Message broker:** Redis Pub/Sub (chosen for simplicity; same instance also serves cache and rate-limiting). Acceptable alternative per brief: RabbitMQ.
- **Database:** Single shared **PostgreSQL** instance with **one schema per microservice** (`auth`, `reception`, `housekeeping`, `room_service`, `maintenance`). Each service owns its schema; cross-schema reads are forbidden — services exchange data only via broker events.
- **WebSocket fan-out:** `ws-gateway` service subscribes to all relevant broker events and pushes them to connected dashboard clients via a single multiplexed WebSocket.
- **Reverse proxy:** Nginx routes `/` → client, `/api/<service>/...` → corresponding FastAPI service, `/ws` → ws-gateway.
- **Orchestration:** Docker Compose. One `docker compose up --build` brings up the entire system.

Do not suggest React/Next.js, MongoDB, or alternative backends — these were explicitly chosen by the user.

## Repository layout (target)

```
hotelos/
├── client/                        # Vue 3 dashboard
│   └── src/
│       ├── views/<resource>/     # List.vue, Detail.vue, Create.vue, Edit.vue per resource
│       ├── stores/                # Pinia stores with optimistic mutations
│       ├── composables/           # useWebSocket, useAuth, useOptimistic
│       └── router/                # Role-guarded routes
├── server/
│   ├── auth-service/              # JWT auth, RBAC, user CRUD
│   ├── reception-service/         # Qabul Servisi
│   ├── housekeeping-service/      # Tozalash Servisi
│   ├── room-service/              # Xona Servisi
│   ├── maintenance-service/       # Texnik Xizmat Servisi
│   └── ws-gateway/                # Broker → WebSocket fan-out
├── nginx/
│   └── nginx.conf
├── design-system/
│   └── hotelos-dashboard/         # Design tokens, page-level overrides (see Design system section)
├── docs/                          # Algorithm flowcharts, ADRs, event catalog, report assets
├── docker-compose.yml
└── .env.example
```

Each FastAPI service follows the same internal layout so a future session can navigate any service without re-learning:

```
server/<service>/
├── manage.py                      # Click CLI: makemigrations, migrate, createmanager, seedusers
├── alembic.ini
├── alembic/
│   └── versions/
├── pyproject.toml
├── Dockerfile
└── src/
    ├── api/                       # FastAPI routers
    ├── core/                      # config, security/hash.py, db, broker
    ├── domain/                    # models, enums, value objects
    ├── infra/repositories/        # SQLAlchemy data access
    ├── services/                  # business logic (algorithms live here)
    └── events/                    # publishers + subscribers for broker
```

## CLI conventions (`manage.py`)

Every service has its own `manage.py` (Click). At minimum auth-service implements:

| Command | Purpose |
|---|---|
| `manage.py makemigrations <message>` | Wraps `alembic revision --autogenerate -m "<message>"`; prints the generated file path. |
| `manage.py migrate` | Wraps `alembic upgrade head`. |
| `manage.py createmanager` | Prompts for phone + password, creates a single top-tier `manager` user. **This is the top role — there is no super_admin.** |
| `manage.py seedusers` | Idempotently seeds one demo user per role so the assessor can log in and run test scenarios immediately. |

User identity is **phone number** (`User.phone`), not email. No public sign-up — initial manager is seeded via CLI, additional staff are created by the manager from the dashboard staff page.

## Roles & permissions

Exactly four roles. Manager is top.

| Role | Pages |
|---|---|
| `manager` | Dashboard, Rooms, Reservations, Guests, Staff, Maintenance (all), Housekeeping queue (all), Room Service orders (all), Reports |
| `reception` | Check-in (room assignment), Check-out (billing), Guest list/profile, Room availability, **Room Service order entry + lifecycle (Received → Preparing → Delivering → Delivered)**, Maintenance issue report |
| `technician` | My maintenance queue (priority-ordered), Issue detail, Mark resolved, History |
| `cleaner` | My cleaning queue, Mark Cleaning → Clean, Room detail |

Every page enforces role via **two layers**:

1. FastAPI dependency: `Depends(require_role(UserRole.MANAGER, UserRole.RECEPTION))`.
2. Vue Router `beforeEnter` guard reading the JWT-decoded role from Pinia.

The sidebar/nav is rendered per role; backend still rejects unauthorized requests independently. Defense in depth.

## Page structure (Vue client)

Pages are **resource-based** with clear list/action separation. Do not stuff form + table + edit into a single page. Standard route shape per resource:

```
/<resource>             → List view (table, filters, search)
/<resource>/new         → Create form
/<resource>/:id         → Detail view (read-only)
/<resource>/:id/edit    → Edit form
```

Plus action-style routes where the workflow demands them:

```
/rooms/:id/check-in
/rooms/:id/check-out
/maintenance/:id/resolve
/orders/:id/advance     # advance order to next lifecycle state
```

Modals are reserved for transient confirmations (delete confirm, quick status change). Never use modals for full forms. Quick inline actions on table rows are allowed (e.g. "Mark Clean") but must follow the optimistic UI rules below.

## Optimistic UI

User-initiated mutations update local state **before** the API responds. The broker-driven WebSocket stream is the source of truth and reconciles.

Pattern in Pinia stores:

1. On user action, mutate local store with `_optimistic: true` flag and revert-on-failure closure.
2. Fire API call.
3. On success → drop the `_optimistic` flag (or wait for confirming WS event).
4. On failure → run the revert closure, show error toast.
5. Incoming WebSocket events from the broker always win. If a server-pushed event contradicts the optimistic state, server wins and the UI re-reconciles.

Apply to:

- Cleaner marking room Clean → row immediately leaves the dirty queue.
- Reception check-in → guest appears as checked-in on the dashboard before the API returns.
- Reception advancing a Room Service order → status badge updates immediately.
- Technician resolving an issue → issue immediately disappears from queue.

## Design system

Persisted at `design-system/hotelos-dashboard/MASTER.md`. **Read it before building any page.** Per-page overrides go under `design-system/hotelos-dashboard/pages/<page-name>.md` — when a page file exists, its rules override MASTER.

Quick highlights (see MASTER.md for the full token set):

- **Style:** Data-Dense Dashboard — KPI cards, data tables, grid layout, minimal padding, maximum data visibility. Light + dark mode both required.
- **Colors:** Primary `#2563EB`, Accent `#059669`, Destructive `#DC2626`. Background `#F8FAFC` / Foreground `#0F172A`.
- **Fonts:** Headings Fira Code, Body Fira Sans (Google Fonts).
- **Avoid:** Ornate decoration; missing filtering/search on lists; emoji as icons (use Lucide/Heroicons SVG).

## The four domain services

Services communicate **only** through the broker. No direct HTTP calls between services. Reception must not import housekeeping models.

| Service (English / Uzbek) | Owns | Publishes | Subscribes to |
|---|---|---|---|
| Reception / Qabul | Guests, check-in, check-out, billing, room service orders | `guest.checked_in`, `guest.checked_out`, `room.vacated`, `bill.finalized`, `order.received`, `order.preparing`, `order.delivering`, `order.delivered`, `order.charged` | `room.cleaned`, `maintenance.resolved` |
| Housekeeping / Tozalash | Cleaning queue, room cleanliness status | `room.cleaning_started`, `room.cleaned` | `room.vacated` |
| Room Service / Xona Servisi | Order persistence & lifecycle store, kitchen-side data | — (consumes reception order events) | `order.received`, `order.preparing`, `order.delivering`, `order.delivered` |
| Maintenance / Texnik Xizmat | Issue reports, priority queue, technician assignment | `maintenance.reported`, `maintenance.assigned`, `maintenance.resolved` | (none required by brief) |

> Note: per the user's decision, **reception both creates AND advances** room service orders. The Room Service microservice still exists as a separate service that consumes the order events and maintains its own kitchen-side projection — this preserves the brief's required "4 services" architecture.

Full event catalog (name, publisher, subscribers, payload schema) lives at `docs/events.md` — required by Task 3.

## Required algorithms (LO1 / Task 1)

Three algorithms must be designed (plain-language steps + flowchart) **before coding**:

1. **Room assignment** (Reception service). Filters in order:
   - Room type match (single / double / suite / accessible)
   - Cleanliness = `Clean` only (exclude `Dirty`, `Cleaning`, `Maintenance`)
   - Longest-clean wins (rotate inventory fairly)
   - Floor preference as secondary filter (fall back to any floor)
   - Proximity preference (elevator/stairs) as final tie-breaker
2. **Billing** (Reception, at check-out): `nightly_rate × nights + Σ room_service_charges + Σ extras − discounts`. Handle early check-out, zero charges, applied discounts.
3. **Maintenance priority queue** (Maintenance service): order by urgency `Critical > High > Normal > Low`; same urgency breaks by submission order (FIFO); assigns to next available technician.

## Mandatory data structures

Implementation must use:

- **Array / list** — room inventory
- **Priority queue** — maintenance requests (Python: `heapq`)
- **Queue** — room service orders (FIFO per kitchen station)
- **Dict / map** — guest records keyed by guest ID

Justify each choice in the report.

## Test scenarios (must all pass)

The assessor runs `TS-01` through `TS-08`. System must not crash on any.

- **TS-06** requires a concurrency guard against double-booking — use `SELECT … FOR UPDATE` on the candidate room row inside a transaction. At least one of the three bugs in the Task 4 debugging log must be a real race condition discovered through this path.
- **TS-07:** "No rooms available" must return a clear message, not crash.
- **TS-08:** Invalid room number must be rejected at the Pydantic boundary with a structured validation error.

Add `tests/test_scenarios.py` per service (or a top-level integration test suite) so every TS-## scenario is a callable test.

## Security requirements (Task 3 + Task 4)

- **Input validation** at the FastAPI boundary using Pydantic models. Document where each external input enters and what is validated.
- **Authentication** — JWT issued by auth-service after phone+password login; verified by every other service via shared JWT public key / shared secret.
- **Data exposure** — WebSocket payloads must not include payment card details, passport numbers, or full billing breakdowns. Define DTOs separate from internal models; the ws-gateway must explicitly project to a redacted shape.
- **Error handling** — register a FastAPI exception handler that catches unhandled exceptions, logs them internally with trace, returns a safe sanitized message. No raw stack traces returned to users.

## Coding standards

Documented in the report (Task 4.4) and consistently applied — the assessor checks code against the claimed standard.

- **Python:** PEP 8, `ruff` for linting, `black` for formatting, type hints required on public functions. `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants.
- **Vue/TS:** ESLint + Prettier. `camelCase` for variables, `PascalCase` for components, `kebab-case` for filenames.
- **Comments:** explain *why*, not *what*. Module-level docstrings on every Python module describing the service's role.
- **No magic numbers** — promote literals (cleaning thresholds, room counts, urgency weights) to named constants in `src/core/constants.py` per service.
- **Functions ≤ ~40 lines** — split when longer. Errors handled at boundaries (FastAPI exception handlers, broker consumers), not scattered through business logic.

## Build & run

```bash
# First time, or after editing docker-compose.yml / Dockerfile / pyproject.toml:
cp .env.example .env
docker compose up --build

# After editing only Python code under server/<service>/src — the src/ tree is
# baked into the image at build time, so a plain `restart` will NOT pick up
# changes. Rebuild the affected service:
docker compose up -d --build reception-service

# Vue dev server hot-reloads automatically (Vite HMR through nginx).

# Seed data once Postgres is healthy:
docker compose exec auth-service       python manage.py seedusers
docker compose exec reception-service  python manage.py seedrooms

# Per-service Alembic migration management:
docker compose exec reception-service python manage.py makemigrations "describe change"
docker compose exec reception-service python manage.py migrate

# Tail logs / inspect state:
docker compose logs -f reception-service
docker compose ps -a
docker compose config --quiet

# Nuke everything (including DB / Redis volumes) when the schema diverges
# from migrations or you want a clean slate:
docker compose down -v
```

Public URL: **http://localhost:8080**. Demo credentials live in `.env`.

## Deliverables (academic)

The brief grades the report (`Familya_Ism_TalabaID_HotelOS_Hisobot.docx`) and code zip (`Familya_Ism_TalabaID_HotelOS_Kod.zip`) together. Word-count budgets apply to written analysis only:

| Task | LO | Word count | Output |
|---|---|---|---|
| 1 — Algorithms & code journey | LO1 | 800–1,200 | Algorithm doc + flowcharts + justification |
| 2 — Programming paradigms | LO2 | 800–1,200 | Annotated code snippets covering procedural, OOP, event-driven |
| 3 — IDE implementation | LO3 | n/a | Working code + IDE evidence screenshots |
| 4 — Debugging & coding standards | LO4 | 600–1,000 | Debug log table (3 bugs incl. one race condition) + standards write-up |

Report formatting: A4, Times New Roman 12pt, line spacing 1.5, margins L 3cm / R 1.5cm / T+B 2cm, Harvard citations (≥ 8 sources), figures numbered with bottom captions, tables numbered with top captions.

Git history must include **≥ 10 meaningful commits** (`git log --oneline` exported into README). Commit messages should narrate the build, not "WIP" / "fix".

## Conventions to avoid

- Do not let services share Python modules across `server/*/` boundaries beyond a tiny `shared/` for event schemas — the assessor checks for microservice independence.
- Do not call one service from another over HTTP. Use the broker.
- Do not skip the algorithm design step. The flowchart must precede the code; the report explicitly grades algorithm-to-code traceability (D1).
- Do not invent bugs for the debugging log. The assessor may ask for git/IDE evidence of the debugging session. Keep real notes as you work.
- Do not scale beyond 2 floors × 10 rooms.
- Do not use Dishka for DI. Do not introduce a super_admin role. Do not cram forms + tables + edits into a single page. Do not send sensitive guest fields over the WebSocket.

## Memory

Long-lived project preferences (stack, DB choice, roles, CLI conventions, page structure, optimistic UI, user profile) are persisted under `/Users/xyron/.claude/projects/-Users-xyron-Desktop-hotelos/memory/` and loaded automatically. Read `MEMORY.md` there before making cross-cutting decisions.
