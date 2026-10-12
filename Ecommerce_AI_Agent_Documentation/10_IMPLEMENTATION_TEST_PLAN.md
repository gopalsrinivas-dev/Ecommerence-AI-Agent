# Implementation and Test Plan

## Build order
Phase 1: initialize repository, configuration, folder structure, migrations, error envelope and request logging.
Phase 2: sessions, CSRF, ownership-scoped orders API and demo fixtures. Verify business rules without an LLM.
Phase 3: transactional pending actions, confirm/dismiss endpoints and audit events. Verify idempotency and concurrency.
Phase 4: provider adapter, allowlisted tools, bounded agent loop and persisted conversations with submission deduplication.
Phase 5: Next.js login, orders, chat and confirmation UI; connect error/retry states.
Phase 6: automated checks, containers, CI, deployment guide and demo walkthrough.

## Unit verification
State transitions; missing/invalid IDs; domain error mapping; unknown tool rejection; argument validation; agent call budgets; deterministic fallback wording; expired/rejected action handling.

## PostgreSQL integration verification
Customer A cannot read/cancel Customer B's order or action. PLACED/PROCESSING cancellation succeeds. SHIPPED/DELIVERED cancellation fails. Cancellation rolls back if audit insert fails. Repeated confirm returns identical saved result. Concurrent confirms do not duplicate mutation/audit. Two different pending actions on same order result in one status transition. Invalid session and expired token reject access. Message deduplication and conversation serialization survive multiple workers using DB constraints/shared execution state.

## Agent verification with a stub provider
Status request selects correct tool. Missing ID asks a question. Unknown tool and fabricated user_id cannot bypass checks. Prompt injection cannot execute SQL or auto-confirm. Multiple tool calls preserve message/tool-call IDs. Provider timeout before/after pending action uses correct error/fallback. Model response cannot overwrite persisted cancellation result.

## Frontend/end-to-end verification
Login -> order list -> chat status. Cancel eligible order -> confirmation -> success -> refreshed status. Keep order -> no mutation. Expired action -> clear retry path. Provider outage -> visible retry. Network loss after confirm -> idempotent reconciliation. Keyboard-only workflow and text-based status announcements.

## Demo script
Sign in as Customer A. Ask 'Where is my order ORD1001?' -> SHIPPED. Ask to cancel ORD1001 -> blocked. Ask to cancel ORD1004 -> confirmation. Select Keep order -> PROCESSING unchanged. Prepare again and confirm -> CANCELLED. Ask about ORD1002 -> unavailable. Replay confirm -> stored successful result.

## Completion checklist
All planned API contracts implemented; migration/seed separation documented; authorization and concurrency tests pass; provider key absent from client bundle; error logs redact secrets; local workflow repeatable; setup README matches actual code; production limitations recorded. This pack defines checks but does not report them as executed against an application.
