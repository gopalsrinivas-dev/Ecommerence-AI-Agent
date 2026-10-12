import { cookies } from "next/headers";
import type { Me } from "./api-client";

export class SessionVerificationError extends Error {
  constructor() {
    super("Unable to verify your session. Please retry.");
  }
}

function unavailable(status: number, code: string, requestId = ""): never {
  // Never log raw bodies, URLs, cookies, or exception messages.
  console.error(
    JSON.stringify({
      event: "session_verification_failed",
      status,
      code,
      request_id: /^[a-f0-9-]{36}$/i.test(requestId) ? requestId : undefined,
    }),
  );
  throw new SessionVerificationError();
}

// Authentication is confirmed by the backend, never inferred from cookie presence.
export async function getSession(): Promise<Me | null> {
  const cookie = (await cookies()).toString();
  let response: Response;
  try {
    response = await fetch(
      `${process.env.BACKEND_URL || "http://127.0.0.1:8001"}/api/v1/auth/me`,
      {
        headers: { cookie },
        cache: "no-store",
        signal: AbortSignal.timeout(10000),
      },
    );
  } catch {
    return unavailable(0, "BACKEND_CONNECTION_FAILED");
  }
  if (response.status === 401) return null;
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const code = body?.error?.code;
    return unavailable(
      response.status,
      [
        "DATABASE_UNAVAILABLE",
        "INTERNAL_ERROR",
        "HTTP_ERROR",
        "RATE_LIMITED",
      ].includes(code)
        ? code
        : "BACKEND_HTTP_ERROR",
      response.headers.get("x-request-id") || "",
    );
  }
  try {
    const me = await response.json();
    if (
      typeof me?.user?.id !== "string" ||
      typeof me?.user?.email !== "string" ||
      typeof me?.provider_mode !== "string"
    )
      throw new Error();
    return me;
  } catch {
    return unavailable(response.status, "INVALID_SESSION_RESPONSE");
  }
}
