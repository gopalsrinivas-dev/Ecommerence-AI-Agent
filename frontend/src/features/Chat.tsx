"use client";
import { useEffect, useRef, useState } from "react";
import { api, Action, Message, Page } from "@/lib/api-client";
import { Feedback } from "@/components/Feedback";
import CancellationCard from "./CancellationCard";
export default function Chat() {
  const [conversation, setConversation] = useState(""),
    [messages, setMessages] = useState<Message[]>([]),
    [input, setInput] = useState(""),
    [busy, setBusy] = useState(false),
    [loading, setLoading] = useState(true),
    [error, setError] = useState<Error | null>(null);
  const retry = useRef<{ id: string; text: string } | null>(null);
  const sending = useRef(false);
  const [submitted, setSubmitted] = useState<string | null>(null);
  async function initialize() {
    setLoading(true);
    setError(null);
    try {
      let identity = sessionStorage.getItem("conversation_id");
      if (!identity) {
        const created = await api<{ conversation_id: string }>(
          "/conversations",
          {},
        );
        identity = created.conversation_id;
        sessionStorage.setItem("conversation_id", identity);
      }
      setConversation(identity);
      let cursor: string | null = null;
      const all: Message[] = [];
      do {
        const page: Page<Message> = await api<Page<Message>>(
          `/conversations/${identity}/messages${cursor ? `?cursor=${cursor}` : ""}`,
        );
        all.push(...page.items);
        cursor = page.next_cursor;
      } while (cursor);
      setMessages(all.sort((a, b) => a.created_at.localeCompare(b.created_at)));
      const saved = sessionStorage.getItem(`pending:${identity}`);
      if (saved) {
        const pending = JSON.parse(saved) as { id: string; text: string };
        retry.current = pending;
        setInput(pending.text);
      }
      const order = new URLSearchParams(location.search).get("order");
      if (order && !saved) setInput(`Please cancel order ${order}`);
    } catch (e) {
      setError(e as Error);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    const timer = setTimeout(() => void initialize(), 0);
    return () => clearTimeout(timer);
  }, []);
  async function send() {
    if (sending.current || !conversation || !input.trim()) return;
    sending.current = true;
    setBusy(true);
    setError(null);
    const pending =
      retry.current?.text === input
        ? retry.current
        : { id: crypto.randomUUID(), text: input };
    retry.current = pending;
    setSubmitted(pending.text);
    sessionStorage.setItem(`pending:${conversation}`, JSON.stringify(pending));
    try {
      const result = await api<{ message: Message; action: Action | null }>(
        "/chat/messages",
        {
          conversation_id: conversation,
          client_message_id: pending.id,
          message: pending.text,
        },
      );
      setMessages((old) => [
        ...old.filter(
          (message) =>
            message.client_message_id !== pending.id &&
            message.id !== result.message.id,
        ),
        {
          id: pending.id,
          role: "user",
          client_message_id: pending.id,
          content: pending.text,
          created_at: new Date().toISOString(),
        },
        { ...result.message, action: result.action },
      ]);
      setInput("");
      retry.current = null;
      sessionStorage.removeItem(`pending:${conversation}`);
    } catch (e) {
      setError(e as Error);
    } finally {
      sending.current = false;
      setBusy(false);
      setSubmitted(null);
    }
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">A HAND WHEN YOU NEED ONE</p>
          <h1>Support assistant</h1>
          <p>Real updates. Clear answers. One less thing to think about.</p>
        </div>
        <span className="availability">
          <span className="online-dot" /> Ready to help
        </span>
      </div>
      <section className="chat-panel">
        <div className="chat-top">
          <span className="assistant-icon">p.</span>
          <div>
            <strong>Parcel assistant</strong>
            <p>Order status & cancellation</p>
          </div>
          <span className="chat-private">◈ Private conversation</span>
        </div>
        <div
          className="message-list"
          aria-live="polite"
          aria-busy={busy || loading}
        >
          {loading ? (
            <p>Loading your conversation…</p>
          ) : messages.length === 0 ? (
            <div className="chat-welcome">
              <span className="welcome-icon">✳</span>
              <h2>Hello. How can we help?</h2>
              <p>
                Check on a delivery or request a cancellation.
                <br />
                Just have your order ID handy.
              </p>
              <div className="suggestions">
                <button onClick={() => setInput("Where is my order ORD1001?")}>
                  Track an order ↗
                </button>
                <button onClick={() => setInput("Please cancel order ORD1004")}>
                  Cancel an order ↗
                </button>
              </div>
            </div>
          ) : (
            messages.map((message) => (
              <div className={`message ${message.role}`} key={message.id}>
                <span className="message-author">
                  {message.role === "user" ? "You" : "Parcel assistant"}
                </span>
                <p>{message.content}</p>
                {message.action && <CancellationCard action={message.action} />}
              </div>
            ))
          )}
          {busy && (
            <div className="message user">
              <span className="message-author">You · sending</span>
              <p>{submitted}</p>
            </div>
          )}
          {busy && (
            <p role="status" className="progress">
              Checking your order securely…
            </p>
          )}
        </div>
        <div className="composer">
          <Feedback
            error={error}
            retry={() => {
              if (conversation) void send();
              else void initialize();
            }}
          />
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void send();
            }}
          >
            <label className="sr-only" htmlFor="message">
              Message the support assistant
            </label>
            <textarea
              id="message"
              placeholder="Ask about your order…"
              value={input}
              maxLength={2000}
              onChange={(e) => setInput(e.target.value)}
              disabled={busy || loading}
              rows={2}
            />
            <button
              className="primary"
              disabled={busy || loading || !conversation || !input.trim()}
            >
              {busy ? "Sending…" : "Send ↑"}
            </button>
          </form>
          <p className="fine-print">
            You’re in control. Cancellations always need your explicit
            confirmation.
          </p>
        </div>
      </section>
    </>
  );
}
