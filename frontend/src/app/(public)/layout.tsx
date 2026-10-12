import { redirect } from "next/navigation";
import { getSession } from "@/lib/session";
import { SessionVerificationError } from "@/lib/session";
import SessionUnavailable from "@/components/SessionUnavailable";
export default async function PublicLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  let me;
  try {
    me = await getSession();
  } catch (error) {
    if (error instanceof SessionVerificationError)
      return <SessionUnavailable />;
    throw error;
  }
  if (me) redirect("/orders");
  return <main className="public-login">{children}</main>;
}
