"use client";
import { useState } from "react";
import { api } from "@/lib/api-client";
import { Feedback } from "@/components/Feedback";
export default function Login() {
  const [error, setError] = useState<Error | null>(null);
  const [busy, setBusy] = useState(false);
  return (
    <section className="panel login-panel">
      <span className="small-icon">↗</span>
      <h1>Welcome back</h1>
      <p>Sign in to your customer account.</p>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          if (busy) return;
          setBusy(true);
          setError(null);
          const data = new FormData(e.currentTarget);
          try {
            await api("/auth/login", {
              email: data.get("email"),
              password: data.get("password"),
            });
            sessionStorage.clear();
            window.location.replace("/orders");
          } catch (e) {
            setError(e as Error);
          } finally {
            setBusy(false);
          }
        }}
      >
        <label htmlFor="email">Email address</label>
        <input
          id="email"
          name="email"
          type="email"
          autoComplete="username"
          required
          placeholder="you@example.com"
        />
        <label htmlFor="password">Password</label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
        />
        <Feedback error={error} />
        <button className="primary full" disabled={busy}>
          {busy ? "Signing in…" : "Sign in →"}
        </button>
      </form>
      <p className="fine-print">
        Your account keeps your orders and support conversations private.
      </p>
    </section>
  );
}
