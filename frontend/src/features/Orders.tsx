"use client";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, Order, Page } from "@/lib/api-client";
import { Badge, Feedback } from "@/components/Feedback";
export default function Orders({ identity }: { identity?: string }) {
  const [orders, setOrders] = useState<Order[]>([]),
    [error, setError] = useState<Error | null>(null),
    [busy, setBusy] = useState(true),
    [cursor, setCursor] = useState<string | null>(null);
  const load = useCallback(
    async (next?: string) => {
      setBusy(true);
      setError(null);
      try {
        if (identity) {
          setOrders([
            await api<Order>(`/orders/${encodeURIComponent(identity)}`),
          ]);
        } else {
          const data = await api<Page<Order>>(
            `/orders${next ? `?cursor=${next}` : ""}`,
          );
          setOrders((old) => (next ? [...old, ...data.items] : data.items));
          setCursor(data.next_cursor);
        }
      } catch (e) {
        setError(e as Error);
      } finally {
        setBusy(false);
      }
    },
    [identity],
  );
  useEffect(() => {
    const timer = setTimeout(() => void load(), 0);
    const refresh = () => void load();
    window.addEventListener("focus", refresh);
    window.addEventListener("orders-updated", refresh);
    return () => {
      clearTimeout(timer);
      window.removeEventListener("focus", refresh);
      window.removeEventListener("orders-updated", refresh);
    };
  }, [load]);
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">YOUR PARCEL, YOUR WAY</p>
          <h1>{identity ? "Order details" : "My orders"}</h1>
          <p>Every order has a story. Here’s where yours stands.</p>
        </div>
        <Link className="button secondary" href="/chat">
          Talk to support ↗
        </Link>
      </div>
      <div className="support-strip">
        <span className="small-icon">◌</span>
        <div>
          <strong>A little help goes a long way.</strong>
          <p>
            Ask our assistant about tracking or cancelling an eligible order.
          </p>
        </div>
        <Link href="/chat">Let’s chat →</Link>
      </div>
      <div className="section-heading">
        <h2>{identity ? "Your order" : "Recent orders"}</h2>
        <span>
          {orders.length} {orders.length === 1 ? "order" : "orders"}
        </span>
      </div>
      <Feedback error={error} retry={() => void load()} />
      {busy && <p role="status">Loading your orders…</p>}
      {!busy && !error && !orders.length && (
        <div className="panel">
          <h2>No orders yet</h2>
          <p>Your next good thing will appear here.</p>
        </div>
      )}
      <div className="orders-grid">
        {orders.map((order, i) => (
          <article className="order-card" key={order.id}>
            <div className={`product-art art-${i % 3}`} aria-hidden>
              <span>
                {order.product_name.includes("headphones")
                  ? "◖◗"
                  : order.product_name.includes("keyboard")
                    ? "▤"
                    : "▱"}
              </span>
            </div>
            <div className="order-content">
              <div className="order-meta">
                <span>{order.order_id}</span>
                <Badge status={order.status} />
              </div>
              <h2>{order.product_name}</h2>
              <p className="muted">
                Updated{" "}
                {new Date(order.updated_at).toLocaleDateString("en-IN", {
                  day: "numeric",
                  month: "short",
                  year: "numeric",
                })}
              </p>
              <div className="order-bottom">
                {identity ? (
                  <Link href={`/chat?order=${order.order_id}`}>
                    {["PLACED", "PROCESSING"].includes(order.status)
                      ? "Request cancellation"
                      : "Ask about this order"}{" "}
                    →
                  </Link>
                ) : (
                  <Link href={`/orders/${order.order_id}`}>
                    View order <span>↗</span>
                  </Link>
                )}
              </div>
            </div>
          </article>
        ))}
      </div>
      {cursor && (
        <button disabled={busy} onClick={() => void load(cursor)}>
          Load more orders
        </button>
      )}
      {identity && (
        <p className="fine-print">
          Cancellation changes the local order state only. Payments and refunds
          are outside this service.
        </p>
      )}
    </>
  );
}
