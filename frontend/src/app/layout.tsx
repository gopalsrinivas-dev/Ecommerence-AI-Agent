import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "Parcel · Customer care",
  description: "Your orders, with thoughtful support.",
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
