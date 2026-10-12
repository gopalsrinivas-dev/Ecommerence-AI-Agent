# Parcel — E-commerce AI Customer Support

Final inspection (12 October 2026): see [verification report](docs/FINAL_VERIFICATION_REPORT.md) and [project guide](docs/PROJECT_GUIDE.md) for current evidence, complete source inventory, exact PostgreSQL startup commands and limitations. Plain-text versions are included. The original specification is preserved as a proposal. The Docker mock/demo application is verified. Live OpenAI, hosted CI and production deployment remain unverified; production is not signed off.

A working Next.js customer portal and FastAPI modular monolith backed by PostgreSQL. Customers can inspect their own orders, ask for status, and prepare cancellation of PLACED or PROCESSING orders. **Only the dedicated confirmation endpoint changes order state.** Cancellation does not process payments, refunds, stock, or external shipments.

## Run with Docker

### Isolated Docker demo alongside native services

Use this verified override when native services occupy 3000/8001/55432. It uses mock/demo mode explicitly, a separate Compose project and named volume, and leaves the native environment files unchanged. Run from the project root in CMD:

```cmd
docker --config .docker-local info
docker --config .docker-local compose version
docker --config .docker-local compose --env-file .env.example -p parcel-docker-verify -f compose.yaml -f compose.verify.yaml up --build -d
docker --config .docker-local compose --env-file .env.example -p parcel-docker-verify -f compose.yaml -f compose.verify.yaml --profile tools run --rm seed
docker --config .docker-local compose --env-file .env.example -p parcel-docker-verify -f compose.yaml -f compose.verify.yaml ps -a
```

Open **http://127.0.0.1:3001** (use this exact host/origin). Fictional application login: **alex@example.test / DemoShop!2026**; Sam is **sam@example.test / DemoShop!2026**. These are application demo accounts, not DB credentials. The frontend shows DEMO MODE. Backend readiness is http://127.0.0.1:8002/api/v1/health/ready; its internal address is http://backend:8000. PostgreSQL is internal only, database ecommerce, persistent volume `parcel-docker-verify_postgres-data`. The Docker session cookie is `parcel_docker_session`; using 127.0.0.1 separates its CSRF cookie from native localhost:3000. Do not substitute localhost:3001 without changing the allowed origin and considering cookie isolation.

The runtime frontend BACKEND_URL is configured as well as its build-time proxy URL, so server-side authentication reaches the container backend. Compose waits for DB health, runs the migration job, then starts backend and frontend. Seed is explicit and preserves existing orders; ORD1004 remains cancelled after the verification walkthrough. Do not reset the volume to repeat a demonstration.

Logs and data-preserving stop/start commands (same root CMD terminal):

```cmd
docker --config .docker-local compose --env-file .env.example -p parcel-docker-verify -f compose.yaml -f compose.verify.yaml logs -f --tail 100 backend frontend
docker --config .docker-local compose --env-file .env.example -p parcel-docker-verify -f compose.yaml -f compose.verify.yaml stop
docker --config .docker-local compose --env-file .env.example -p parcel-docker-verify -f compose.yaml -f compose.verify.yaml up -d
```

Ctrl+C exits log following without stopping containers. `stop`/`up -d` preserve the database volume. Never use `down -v` or delete volumes. The override uses Compose `!override` for frontend ports (requires Compose 2.24.4+; verified with v5.1.4). This is a local HTTP demo, not production deployment. See the final verification report's Docker follow-up for executed results.

### Default Docker topology

Requires Docker Desktop with Linux containers running. From this project root:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up --build
```

In another terminal, explicitly seed the local demo:

```powershell
docker compose --profile tools run --rm seed
```

Open http://localhost:3000. The migration service waits for PostgreSQL readiness, applies Alembic once, and the application waits for that service. PostgreSQL persists in the `postgres-data` volume and has no published host port. Only the frontend is published, bound to localhost. Production requires a separately configured HTTPS ingress.

Seed is idempotent and preserves existing orders; it does **not** reset a cancelled order. It is forbidden with `APP_ENV=production` and never runs at startup. `docker compose down` preserves the database volume.

## Demo accounts

| Customer | Email | Password | Orders |
|---|---|---|---|
| Alex | alex@example.test | DemoShop!2026 | ORD1001 SHIPPED, ORD1003 CANCELLED, ORD1004 PROCESSING |
| Sam | sam@example.test | DemoShop!2026 | ORD1002 DELIVERED |

These fictional local credentials are intentionally public demo data. Do not seed a production database.

## Native Windows startup (CMD, port 8001)

This workspace uses Python **3.14.6 x64**, psycopg **3.3.6**, and the existing PostgreSQL **18.4 libpq** in `D:\Workspace\softwares\PostgreSQL\18\bin`. The installed `psycopg-binary` wheel is correctly tagged `cp314-cp314-win_amd64`, but Windows Application Control blocks its compiled extension. Reinstalling that same wheel does not resolve a policy denial. No security policy was disabled and no driver replacement was needed.

The working solution is psycopg's [documented pure Python implementation](https://www.psycopg.org/psycopg3/docs/basic/install.html), loading the existing PostgreSQL installation's `libpq.dll` and dependencies. The installed libpq is unsigned but was allowed to load by the current policy; the wheel's extension remains blocked. Keep the installed PostgreSQL `bin` DLLs together (including `libssl-3-x64.dll`, `libcrypto-3-x64.dll`, `libintl-9.dll`, and `libiconv-2.dll`); do not copy individual DLLs into the repository or Python installation.

`backend/.env` is already configured locally. It is ignored by git. To reproduce on another installation, add this non-secret setting to that file, adapting the path:

```dotenv
POSTGRES_BIN=D:\Workspace\softwares\PostgreSQL\18\bin
```

On Windows, the backend uses this explicit installed directory before SQLAlchemy imports the driver: it registers the DLL directory, sets process-local PATH discovery, and defaults `PSYCOPG_IMPL` to `python`. It does not alter global PATH, weaken security, or silently switch database drivers. Explicit `PSYCOPG_IMPL` choices are respected. Linux/Docker keep the existing binary driver. `DATABASE_URL` remains `postgresql+psycopg://...`; keep credentials in `backend/.env` and do not print that file.

Run these exact commands in **Windows Command Prompt (CMD)**, not PowerShell. The environment is at the project root; backend commands run inside `backend`:

```cmd
cd /d D:\Workspace\professional\AgenticAI\Ecommerence-AI-Agent
set "PSYCOPG_IMPL=python"
set "PATH=D:\Workspace\softwares\PostgreSQL\18\bin;%PATH%"
.venv\Scripts\python.exe -c "import psycopg; print('Driver:', psycopg.pq.__impl__, 'libpq:', psycopg.pq.version())"
cd backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --no-access-log
```

Alternatively, after `.env` configuration, run `scripts\start-backend.cmd` from the project root. That launcher uses the root virtual environment and backend working directory without requiring activation. For first-time setup only, create `.venv`, install `backend/requirements.lock`, copy `.env.example` without overwriting existing configuration, configure your database, migrate, then explicitly run `python -m scripts.seed_demo` from `backend` for fictional demo data. Do not reinstall dependencies to fix the existing policy block.

In a **second CMD terminal**:

```cmd
cd /d D:\Workspace\professional\AgenticAI\Ecommerence-AI-Agent\frontend
set "BACKEND_URL=http://127.0.0.1:8001"
npm.cmd run dev
```

Use `npm.cmd ci` first only if dependencies are missing. Native `frontend/.env.local` and `.env.example` target port 8001. Existing Next.js processes must be restarted after changing the proxy. For a production build, run `npm.cmd run build` with the same `BACKEND_URL`, then `npm.cmd start`: rewrites are captured at build time.

Verify from a third CMD terminal:

```cmd
curl.exe -f http://127.0.0.1:8001/api/v1/health/live
curl.exe -f http://127.0.0.1:8001/api/v1/health/ready
curl.exe -f http://localhost:3000/api/v1/health/ready
```

Browse **http://localhost:3000**, matching `FRONTEND_ORIGIN`. Do not substitute `http://127.0.0.1:3000`: it is a different browser origin and login is intentionally rejected (403). If using another hostname, configure `FRONTEND_ORIGIN` to that exact trusted origin and restart the backend. Swagger is http://127.0.0.1:8001/docs. Browser UI uses the same-origin `/api` proxy. Docker and CI explicitly retain their internal backend port 8000 through `BACKEND_URL`; the native default is 8001.

For PostgreSQL integration tests, use a separate disposable database whose name contains `test`, as described below. With the current isolated workspace cluster running, these CMD commands run the full suite without displaying credentials:

```cmd
cd /d D:\Workspace\professional\AgenticAI\Ecommerence-AI-Agent\backend
set "PSYCOPG_IMPL=python"
set "PATH=D:\Workspace\softwares\PostgreSQL\18\bin;%PATH%"
set "TEST_DATABASE_URL=postgresql+psycopg://app@127.0.0.1:55432/ecommerce_test"
set "DATABASE_URL=%TEST_DATABASE_URL%"
..\.venv\Scripts\python.exe -m pytest -q
```

This isolated local cluster must be running; it does not modify the separately installed PostgreSQL service. If Windows policy later blocks the installed libpq or a dependency, startup will still fail: ask the machine administrator for an approved PostgreSQL installation/policy decision. Do not disable Smart App Control. A compiled mypy policy block can separately be handled with a pure Python mypy installation; it is unrelated to database connectivity.

## Environment and providers

Templates: root `.env.example` for Compose; `backend/.env.example` for native backend; `frontend/.env.example` for native Next.js. Real `.env` files are ignored. Backend configuration uses pydantic-settings and validates PostgreSQL dialect, positive execution limits, real-provider credentials, and production mode.

- `PROVIDER_MODE=mock`: explicit development/test demo. The UI displays a demo banner. The mock selects tools, and the same ownership and cancellation services execute them.
- `PROVIDER_MODE=openai`: set backend-only `OPENAI_API_KEY` and `OPENAI_MODEL` to an available tool-capable Chat Completions model. No model identifier is assumed. There is no fallback to mock mode on provider failure.
- Production: `APP_ENV=production`, `PROVIDER_MODE=openai`, HTTPS `FRONTEND_ORIGIN`, runtime DB credentials. Cookies become Secure. Mock mode and demo database passwords are rejected.
- Session lifetime: 8 hours; action expiry: 5 minutes; turn deadline: 30 seconds; at most 4 model requests and 4 tools; provider request timeout: 10 seconds. All are configurable using the template.
- Authentication rate: 10 requests/minute per connection source; chat: 10/minute per authenticated actor. Counters live in PostgreSQL, shared across workers. With the Next.js proxy, login source limiting conservatively shares the proxy source bucket; tune this for load and deploy a trusted ingress IP limiter before public launch. Forwarded client IP headers are deliberately not trusted.

The provider follows the [official OpenAI function-calling contract](https://developers.openai.com/api/docs/guides/function-calling). The backend validates tool names and arguments, injects the session actor, preserves assistant/tool call IDs, bounds history, and executes tools itself. There is one bounded retry of a failed safe provider request, counted against model-call and time budgets. Customer-visible order answers are deterministic templates from database results; arbitrary model prose cannot assert an order status or successful mutation.

Run `python -m scripts.maintenance` from `backend` periodically (or `docker compose exec backend python -m scripts.maintenance`) to remove expired/revoked sessions and old rate buckets and expire pending actions. Schedule it with Windows Task Scheduler or your deployment scheduler. Chat and audit deletion are intentionally excluded until retention policy is approved.

## Architecture and files

```text
backend/
  app/api/               routes and authenticated/CSRF dependencies
  app/core/              settings, safe errors, security, structured logs
  app/db/                pooled SQLAlchemy sessions
  app/models/            persisted records and constraints
  app/schemas/           validated request and tool contracts
  app/repositories/      ownership-scoped persistence access
  app/services/          authentication, orders/actions, queries, chat turns
  app/agents/            explicit allowlisted, bounded tool loop
  app/integrations/      real OpenAI and explicit mock adapters
  migrations/            self-contained Alembic schema migration
  scripts/               explicit local demo seed
  tests/                 agent and PostgreSQL security/concurrency tests
frontend/
  src/app/               App Router login, orders, order detail, chat, errors
  src/features/          order/chat workflows and cancellation card
  src/components/        navigation, status and error presentation
  src/lib/               same-origin typed API client
  tests/                 interaction tests
  e2e/                   Playwright customer workflow
  scripts/               standalone production server startup
compose.yaml             persistent PostgreSQL, migrations, apps, explicit seed
.github/workflows/ci.yml  locked installs, validation and browser workflow
docs/IMPLEMENTATION_STATUS.md
Ecommerce_AI_Agent_Documentation/  original specification, preserved
```

Routes call services; tools call the same order service. Repositories scope resources to the session actor; services own transactions. Confirmation locks the owned action first, then the owned order. Status, action result and cancellation audit commit together. Audit failure rolls back everything. Separate actions on an already cancelled order record an `already_cancelled` result without another transition or audit event. Repeated confirmation returns the saved result without using a provider.

Backend domain definitions are organized into real modules rather than implemented in package `__init__.py` files:

- `app/models/`: `base.py` contains the shared SQLAlchemy Base, Record mixin and UTC clock; `user.py`, `session.py`, `order.py`, `conversation.py`, `message.py`, `action.py` (PendingAction), `audit_event.py`, `turn.py` (chat Turn), and `rate_bucket.py` contain the nine mapped entities. The package initializer only registers/re-exports those definitions so Alembic always sees the complete metadata.
- `app/schemas/`: `base.py` contains StrictInput; `auth.py`, `order.py`, `chat.py`, `action.py`, and `error.py` contain their API/agent contracts. ErrorResponse describes the existing centralized error envelope. Import schemas from their domain modules.
- `app/repositories/`: `users.py`, `orders.py`, `conversations.py`, `actions.py`, `sessions.py`, `rate_limits.py`, and `health.py` contain queries; `base.py` contains the shared ownership-scoped lookup. Chat message pagination, recent history and turn lookup live in `conversations.py`. Repository functions do not commit; services retain the original transaction boundaries.

Originally, all mapped entities, Pydantic schemas and repository query functions were defined directly inside their respective `__init__.py` files, making these directories appear empty in a collapsed file tree. The split preserves table names, constraints, indexes, foreign keys, API shapes and migration revision; it requires no schema or data migration. Services, agents, routes, tests and migration tooling use explicit domain imports; model compatibility exports refer to the same class objects, with no duplicate definitions.

Chat submission is unique by `(conversation_id, client_message_id)` and binds that ID to a content hash. A row-locked conversation lease serializes work across processes. Provider calls hold no database locks. Expired leases can be reclaimed; per-tool and completion fencing prevents an abandoned worker from writing after recovery. Pending preparation is unique per turn/order, so a retry reuses its action. Failed turns can retry with the original ID. The browser stores its conversation and pending retry ID per tab and reloads persisted history.

Opaque session tokens and CSRF tokens are random; only their hashes are stored. Session cookies are HttpOnly/SameSite Lax and Secure in production. Mutations require the exact origin and a session-bound CSRF header; login requires the exact origin to prevent login CSRF. Errors use a stable envelope and a server-generated request ID. Operational JSON logs allowlist fields and omit passwords, cookies, tokens, keys, database URLs, customer text, and provider payloads. Business audits are separate transactional records.

## API

Swagger: http://127.0.0.1:8001/docs; OpenAPI: `/openapi.json`. API prefix `/api/v1`:

```text
POST /auth/login             POST /auth/logout           GET /auth/me
GET  /orders                 GET  /orders/{order_id}
POST /conversations          GET  /conversations/{id}/messages
POST /chat/messages
POST /actions/{action_id}/confirm
POST /actions/{action_id}/dismiss
GET  /health/live            GET /health/ready
```

Orders/history accept `limit=1..100` and an opaque `cursor`, returning `items` and `next_cursor`. Unowned and absent resources both return generic 404. Chat errors 409/429/503/504 can be retried where marked; re-use `client_message_id` and the same message. Confirm is idempotent by server-issued action ID. The cancellation card explicitly offers reconciliation after a lost response.

## Tests and production build

Use a **separate PostgreSQL database whose name contains `test`**. Integration fixtures reset application tables in that database. Never point tests at valuable data.

```powershell
Set-Location backend
$env:TEST_DATABASE_URL = 'postgresql+psycopg://app:your_password@localhost:5432/ecommerce_test'
$env:DATABASE_URL = $env:TEST_DATABASE_URL
..\.venv\Scripts\python -m alembic upgrade head
..\.venv\Scripts\ruff check .
..\.venv\Scripts\ruff format --check .
..\.venv\Scripts\python -m mypy app
..\.venv\Scripts\python -m pytest -q
Set-Location ../frontend
npm.cmd ci
npm.cmd run typecheck
npm.cmd run lint
npm.cmd test
npm.cmd run build
npm.cmd exec -- playwright install chromium
```

For E2E, start both applications against a **fresh demo database**, migrate and seed it, then run `npm.cmd run e2e` from `frontend`. The test deliberately cancels ORD1004; subsequent runs need a fresh demo database. Test fixtures do not modify your demo database. CI provisions separate test and E2E databases. For native production-build smoke checks, use `npm.cmd start` after `npm.cmd run build` (the startup script copies static assets and launches Next.js standalone output).

## Limitations

This is a verified local implementation, not a production-readiness claim. Real OpenAI access needs your key/model and has not been exercised without credentials. The isolated Docker mock stack passed build, migrations, browser/API and restart-persistence checks; see the Docker follow-up in the final report. Public launch still needs TLS/ingress configuration, backup/restore drills, monitoring, load and security testing, customer provisioning/password recovery, retention decisions, and scheduled data cleanup. No refunds, payments, inventory, carrier integration, administrative UI, vector database, RAG, or arbitrary-code tools are included. The browser keeps one active conversation per tab; a conversation-list interface is outside this MVP.

### Login and session layout

If `/login` reports session verification unavailable, check backend `/api/v1/health/ready` as well as `/api/v1/health/live`. A live backend can return `503 DATABASE_UNAVAILABLE` when PostgreSQL is stopped. The native workspace database is configured separately in `backend/.env`; start that configured cluster before starting the backend. Do not change credentials or reseed to resolve a stopped database. Session verification failures display a service-unavailable view with Retry and withhold protected content. Only an explicit 401 is treated as unauthenticated. Server diagnostics retain HTTP status, allowlisted error code and backend request ID without raw response bodies or cookies.

`/login` uses the public layout and displays only the sign-in panel. Protected routes use a separate authenticated layout: the Next.js server forwards the incoming cookies to the configured backend `/api/v1/auth/me` with caching disabled before rendering application navigation. A cookie alone does not establish authentication. Anonymous or invalid sessions redirect to `/login`; authenticated visits to `/login` redirect to `/orders`. Login/logout use a full navigation to discard cached private UI. Backend session, origin, ownership and CSRF checks remain authoritative.

With the existing backend on port 8001 and frontend on `http://localhost:3000`, verify the authentication flow from Windows CMD:

```cmd
cd /d D:\Workspace\professional\AgenticAI\Ecommerence-AI-Agent\frontend
npm.cmd run typecheck
npm.cmd run lint
npm.cmd test
npm.cmd run e2e -- e2e/auth.spec.ts --trace off
```

The browser test checks anonymous protected routes, invalid credentials, successful login, cookie flags, `/auth/me`, refresh, authenticated-login redirect, chat navigation, missing-CSRF rejection, logout cookie removal, and invalid-session rejection. It does not cancel or modify orders. Restart the frontend after moving route layouts if an existing development process still serves an old root layout.

### Operational logs

Set backend `LOG_FORMAT=auto` (default), `console`, or `json`. Auto uses readable single-line console output in development and structured JSON when `APP_ENV=production`. Restart the backend after changing configuration. Run Uvicorn with `--no-access-log` (as the launcher does) to avoid a second access log containing raw URLs.

Example development completion (abbreviated):

```text
level="INFO" event="request_completed" request_id="…" method="POST" path="/api/v1/actions/{identity}/confirm" route_template="/api/v1/actions/{identity}/confirm" action="confirm" status_code=200 duration_ms=12
```

Example production completion:

```json
{"timestamp":"2026-10-11T18:00:00+00:00","level":"INFO","event":"request_completed","request_id":"68df9c85-efb7-427c-8b70-fd45c77fcd92","method":"GET","path":"/api/v1/orders/{order_id}","route_template":"/api/v1/orders/{order_id}","action":"order","status_code":200,"duration_ms":8}
```

`path` is deliberately normalized to the matched route template; unknown routes use `<unmatched>`. Query strings and arbitrary path parameters never enter operational logs. Server-generated request IDs connect request, service, agent/tool, provider and error events; authenticated actor UUIDs and relevant conversation/action UUIDs or validated order IDs provide safe correlation. Numeric status and duration fields remain JSON numbers. Bodies, headers, credentials, customer/provider messages and exception text are excluded. Error logs retain redacted stack frames.

Business events include `login_succeeded`, `login_failed`, `logout_succeeded`, `order_looked_up`, `orders_looked_up`, `agent_turn_started`, `agent_turn_completed`, `tool_selected`, `tool_completed`, and cancellation events `cancellation_prepared`, `cancellation_dismissed`, `cancellation_rejected`, `cancellation_expired`, `cancellation_committed`, `cancellation_replayed`. Preparation is emitted only after commit and discarded on rollback. Committed cancellation uses `outcome=mutated` for a new order mutation or `outcome=already_cancelled` when another action already cancelled it. Repeating a completed confirmation emits `cancellation_replayed` with `replay=true`, without another committed event. Operational logs are best-effort diagnostics, not a durable audit/outbox; transactional business audits remain authoritative.

`backend/tests/test_logging.py` covers concurrent request correlation, route/action fields, numeric JSON fields, redaction, output formats, logger failures, preparation rollback, confirmation rollback and committed/replayed cancellation.

### API error handling

API errors use `{ "error": { "code": "...", "message": "...", "retryable": false }, "request_id": "..." }` and the matching `X-Request-ID` response header. Central handlers cover request validation (422), HTTP exceptions (original status and headers), business errors, SQLAlchemy failures (503), and unexpected failures (500). Authentication, CSRF and ownership retain their domain codes and statuses. Unexpected/database failures are logged once at the request boundary with redacted stack frames: exception messages, SQL parameters, source lines and local values are omitted.

Request database sessions and chat transactions explicitly roll back on failure. Chat lease cleanup runs in a separate transaction; cleanup failures are logged without replacing the original operation failure. Cancellation confirmation commits the order, action and audit together and never invokes AI generation. Its committed result remains durable and retries return that result even if a later chat/provider request fails.

`backend/tests/test_errors.py` covers envelope consistency, required HTTP headers, redacted exception logging, provider timeout/connection translation, rollback on cancellation audit/commit failure, and cleanup failure. `frontend/tests/errors.test.tsx` verifies customer feedback consumes the envelope and retains its retryability and support request ID. Backend database tests require a separate `TEST_DATABASE_URL` whose database name contains `test`; they reset that test schema.
