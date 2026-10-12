# Security, Error Handling and Logging

## Authentication and authorization
Hash passwords using a maintained password hashing library. Use high-entropy opaque session tokens; store hashes in DB. Secure, HttpOnly, SameSite cookies with explicit expiry and revocation. Use a CSRF token/header plus origin checks for state-changing requests. Apply authorization to routes, repositories, tool adapters, actions and conversation history. Use generic 404 for unowned resources to reduce enumeration.

## Secrets and input
Backend-only OPENAI_API_KEY and database credentials. Never put secrets in NEXT_PUBLIC_ variables. Ignore .env in git; commit only .env.example. Parameterized queries. Validate input lengths and allowed IDs. Avoid provider-generated SQL. Exact CORS allowlist if separate origins are used; never wildcard credentialed CORS.

## Errors
Domain exceptions carry stable error codes. A central handler converts them into the API error envelope. Roll back failed DB transactions. Log internal stack traces only on unexpected failures. Frontend displays safe messages and request ID. Provider timeout and unavailable errors remain distinguishable internally. Do not return raw tracebacks, connection strings or SQL to users.

## Logging events
request_started, request_completed, agent_turn_started, tool_selected, tool_completed, pending_action_created, cancellation_confirmed, cancellation_rejected, provider_failed and unexpected_error.

Fields: timestamp UTC, level, event, request_id, conversation_id where applicable, action_id, pseudonymous actor ID, tool_name, duration_ms, outcome, error_code. Attach stack trace only for server exceptions. Redact Authorization/cookies/tokens/passwords/provider keys and message/customer content by default. Avoid logging full provider payloads.

## Audit versus operational logs
Audit events record business actions inside the mutation transaction. Operational logs track system behavior and may be shipped externally. Successful cancellation must not rely solely on console logs. Restrict audit access and define retention before launch.

## Reliability
Use connection pooling, bounded provider retries with jitter, provider timeouts and request deadlines. Retry transient reads safely; never re-run external side effects without idempotency. If audit write fails, roll back cancellation. On DB outage, report unavailable rather than falling back to invented data. Track latency, errors, provider token use, tool failures and confirmation outcomes.
