"use client";
import { useEffect, useState } from "react";
import { Action, api, ApiError } from "@/lib/api-client";
import { Feedback } from "@/components/Feedback";
export default function CancellationCard({ action }: { action: Action }) {
  const [state, setState] = useState(action.state),
    [busy, setBusy] = useState(false),
    [error, setError] = useState<Error | null>(null),
    [uncertain, setUncertain] = useState(false);
  useEffect(() => {
    if (state !== "PENDING") return;
    const timer = setTimeout(
      () => setState("EXPIRED"),
      Math.max(0, new Date(action.expires_at).getTime() - Date.now()),
    );
    return () => clearTimeout(timer);
  }, [action.expires_at, state]);
  async function act(confirm: boolean) {
    setBusy(true);
    setError(null);
    try {
      const result = await api<{ state: string }>(
        `/actions/${action.id}/${confirm ? "confirm" : "dismiss"}`,
        {},
      );
      setState(result.state);
      setUncertain(false);
      window.dispatchEvent(new Event("orders-updated"));
    } catch (e) {
      setError(e as Error);
      if (e instanceof ApiError && e.status === 410) setState("EXPIRED");
      else if (e instanceof ApiError && e.status === 409) setState("REJECTED");
      else if (confirm) setUncertain(true);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section
      className="confirmation"
      aria-label={`Cancellation for ${action.order_id}`}
    >
      <p className="eyebrow">
        {state === "COMPLETED"
          ? "CANCELLATION COMPLETE"
          : "YOUR CONFIRMATION NEEDED"}
      </p>
      <h3>{action.product_name}</h3>
      <p>{action.order_id}</p>
      <p aria-live="polite">
        {busy
          ? "Checking your request…"
          : state === "COMPLETED"
            ? "Your order is cancelled."
            : state === "EXPIRED"
              ? "This confirmation expired. Ask for a new cancellation request."
              : state === "REJECTED"
                ? "This request is closed. Your order has not been changed by this request."
                : "Cancel this order? This updates its local status only; no refund is processed."}
      </p>
      <Feedback error={error} />
      {(state === "PENDING" || uncertain) && (
        <div className="button-row">
          <button
            className="danger"
            disabled={busy}
            onClick={() => void act(true)}
          >
            {uncertain ? "Check cancellation result" : "Confirm cancellation"}
          </button>
          <button disabled={busy || uncertain} onClick={() => void act(false)}>
            Keep order
          </button>
        </div>
      )}
    </section>
  );
}
