export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public requestId = "",
    public code = "",
    public retryable = false,
  ) {
    super(message);
  }
}
export async function api<T>(path: string, body?: unknown): Promise<T> {
  const csrf =
    typeof document === "undefined"
      ? ""
      : document.cookie
          .split("; ")
          .find((x) => x.startsWith("csrf_token="))
          ?.split("=")[1] || "";
  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, {
      method: body === undefined ? "GET" : "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": decodeURIComponent(csrf),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store",
    });
  } catch {
    throw new ApiError("Connection interrupted. Please retry.", 0);
  }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    if (response.status === 401 && !path.includes("/auth/login")) {
      sessionStorage.clear();
      // A full reload clears all in-memory private customer data on expiry.
      window.location.assign("/login");
    }
    throw new ApiError(
      data.error?.message || "Unable to complete this request.",
      response.status,
      data.request_id,
      data.error?.code,
      data.error?.retryable === true,
    );
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
export type Order = {
  id: string;
  order_id: string;
  product_name: string;
  status: string;
  updated_at: string;
  version: number;
};
export type Action = {
  id: string;
  order_id: string;
  product_name: string;
  state: string;
  expires_at: string;
  result?: { order_status: string };
};
export type Message = {
  client_message_id?: string | null;
  id: string;
  role: string;
  content: string;
  created_at: string;
  action?: Action | null;
};
export type Page<T> = { items: T[]; next_cursor: string | null };
export type Me = { user: { id: string; email: string }; provider_mode: string };
