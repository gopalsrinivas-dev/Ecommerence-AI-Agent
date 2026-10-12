"use client";

export default function SessionUnavailable() {
  return (
    <main className="public-login">
      <section role="alert">
        <h1>Service temporarily unavailable</h1>
        <p>Unable to verify your session. Please retry.</p>
        <button onClick={() => window.location.reload()}>Retry</button>
      </section>
    </main>
  );
}
