import Link from "next/link";
export default function Missing() {
  return (
    <section className="panel">
      <h1>Page unavailable</h1>
      <Link href="/orders">Back to your orders</Link>
    </section>
  );
}
