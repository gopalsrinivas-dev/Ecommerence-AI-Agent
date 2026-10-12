# Frontend Design

Use Next.js with React and TypeScript. Use a single web frontend, responsive on desktop/mobile.

## Pages
/login: labeled email/password controls, generic authentication error.
/orders: customer order cards, status labels, pagination and empty state.
/orders/[orderId]: product, status, update time and eligible cancellation entry point.
/chat: message history, composer, pending action cards and service-status feedback.

## Chat behavior
Show user message immediately with sending indicator. Disable duplicate submissions while a turn is running. Preserve unsent text after failure. Show loading text rather than an indefinite spinner alone. Keep retry tied to client_message_id. Do not invent an assistant reply while waiting for the server. Reload persisted history when reopening conversation.

## Cancellation card
Show exact order ID, product and effect: 'Cancel this order'. Buttons: Confirm cancellation and Keep order. Use action_id from server; never trust order IDs extracted from rendered AI text. Show pending/confirming/completed/expired/rejected states. On timeout fetch/reconcile persisted status by retrying the idempotent confirm endpoint. Refresh the order view after completion. Clarify that refund handling is outside this MVP.

## Error states
401 -> sign-in screen; 404 -> resource unavailable; 409 -> refresh order/action; 410 -> request a new action; 429 -> retry delay; 503/504 -> retry control. Keep request ID visible in expandable error detail for support.

## Accessibility
Keyboard navigation, visible focus, semantic buttons, sufficient contrast, text labels for all status information, aria-live for new responses. No audio-only interaction; complete workflow must work through text. Render assistant output as escaped text or sanitized limited Markdown; never execute returned HTML.
