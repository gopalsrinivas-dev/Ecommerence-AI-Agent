import { redirect } from "next/navigation";
import Shell from "@/components/Shell";
import { getSession } from "@/lib/session";
import { SessionVerificationError } from "@/lib/session";
import SessionUnavailable from "@/components/SessionUnavailable";
export default async function AuthenticatedLayout({
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
  if (!me) redirect("/login");
  return <Shell initialSession={me}>{children}</Shell>;
}
