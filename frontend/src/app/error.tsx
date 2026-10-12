"use client";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <section className="panel">
      <h1>Let’s try that again</h1>
      <p>We couldn’t load this page.</p>
      <button onClick={reset}>Retry</button>
    </section>
  );
}
