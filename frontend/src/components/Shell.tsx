"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { api, Me } from "@/lib/api-client";
export default function Shell({
  children,
  initialSession,
}: {
  children: React.ReactNode;
  initialSession: Me;
}) {
  const path = usePathname();
  const [me, setMe] = useState<Me | null>(initialSession);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  if (!me) return null;
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link className="brand" href="/orders">
          <span className="brand-icon">p</span> parcel
          <span className="brand-dot">.</span>
        </Link>
        <p className="nav-label">YOUR ACCOUNT</p>
        <nav aria-label="Main navigation">
          <Link
            className={path.startsWith("/orders") ? "active" : ""}
            href="/orders"
          >
            <span aria-hidden>▦</span> My orders
          </Link>
          <Link className={path === "/chat" ? "active" : ""} href="/chat">
            <span aria-hidden>◌</span> Support assistant
          </Link>
        </nav>
        <div className="sidebar-note">
          <span className="online-dot" /> Here to help
          <p>Order updates and a little peace of mind, all in one place.</p>
        </div>
        {me && (
          <div className="account">
            <span className="avatar">{me.user.email[0].toUpperCase()}</span>
            <div>
              <strong>{me.user.email.split("@")[0]}</strong>
              <button
                className="text-button"
                disabled={busy}
                onClick={async () => {
                  if (busy) return;
                  setBusy(true);
                  try {
                    await api("/auth/logout", {});
                    sessionStorage.clear();
                    setMe(null);
                    window.location.replace("/login");
                  } catch (e) {
                    setError((e as Error).message);
                    setBusy(false);
                  }
                }}
              >
                Sign out
              </button>
            </div>
          </div>
        )}
      </aside>
      <div className="main-area">
        <header>
          <span>Customer care, made simple</span>
          <span className="secure">◈ Secure customer portal</span>
        </header>
        {me?.provider_mode === "mock" && (
          <div className="demo-banner">
            DEMO MODE{" "}
            <span>
              Local mock assistant · real order rules and confirmation checks
            </span>
          </div>
        )}
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <main>{children}</main>
        <footer>
          Thoughtful support. Every step of the way.
          <span>Parcel customer care</span>
        </footer>
      </div>
    </div>
  );
}
