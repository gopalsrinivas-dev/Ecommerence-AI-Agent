E-commerce AI Customer Support Agent — Documentation Pack

Prepared: 11 October 2026. Status: proposed implementation specification; application code has not been built or tested in this delivery.

Purpose
Build a small, professionally structured application where customers can ask about their own orders and request cancellation. Use Next.js (React/TypeScript), FastAPI (Python), and PostgreSQL. Keep the agent tools and business rules separate.

Reading order
1. 01_REQUIREMENTS — purpose, features, scope, acceptance criteria.
2. 02_ARCHITECTURE — components and request flow.
3. 03_FOLDER_STRUCTURE — planned files and responsibilities.
4. 04_DATABASE_DESIGN — tables, constraints, transactional rules.
5. 05_API_CONTRACTS — endpoints, payloads, errors.
6. 06_AGENT_WORKFLOW — tool contracts, confirmation and bounded execution.
7. 07_FRONTEND_DESIGN — pages, UI states, accessibility.
8. 08_SECURITY_ERROR_LOGGING — authorization, errors, logs.
9. 09_SETUP_DEPLOYMENT — environment, dependency categories, deployment.
10. 10_IMPLEMENTATION_TEST_PLAN — build sequence and verification.
11. 11_SOURCE_REVIEW — archive evidence and corrections.

Every document is provided in Markdown and plain text. ALL_DOCUMENTS contains the complete set in one file, in both formats.

Telugu-English explanation
Idi customer support application. Customer tana order status adagochu; eligible order cancel cheyyadaniki confirmation ivvachu. AI question ni understand chesi correct tool suggest chesthundi. Backend ownership, permissions, order rules validate chesina tarvatha database action chesthundi. Database result aadhaaramga answer isthundi.

Next.js lo React already untundi; separate React application avasaram ledu. PostgreSQL business data kosam. Ee first version ki RAG/vector database/MCP mandatory kaadu.

Decisions used for this plan
Authenticated customer owns each order. Only PLACED and PROCESSING orders can be cancelled. Cancellation needs an explicit UI confirmation. These are proposed rules, not rules established by the screenshots; confirm business policy before a real launch.
