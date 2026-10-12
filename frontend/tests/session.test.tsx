import { beforeEach, expect, test, vi } from "vitest";
import { getSession, SessionVerificationError } from "@/lib/session";
import PublicLayout from "@/app/(public)/layout";
import AuthenticatedLayout from "@/app/(authenticated)/layout";

vi.mock("next/headers", () => ({
  cookies: async () => ({ toString: () => "ecommerce_session=test-token" }),
}));
vi.mock("next/navigation", () => ({ redirect: vi.fn() }));
vi.mock("@/components/Shell", () => ({ default: () => null }));

beforeEach(() => {
  vi.restoreAllMocks();
});

test("401 is anonymous and incoming cookies are forwarded without caching", async () => {
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValue(new Response(null, { status: 401 }));
  expect(await getSession()).toBeNull();
  expect(fetcher).toHaveBeenCalledWith(
    expect.stringContaining("/api/v1/auth/me"),
    expect.objectContaining({
      headers: { cookie: "ecommerce_session=test-token" },
      cache: "no-store",
    }),
  );
});

test.each([403, 500, 503])(
  "HTTP %s fails closed with safe diagnostics",
  async (status) => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          error: { code: "DATABASE_UNAVAILABLE", message: "secret" },
        }),
        { status },
      ),
    );
    const log = vi.spyOn(console, "error").mockImplementation(() => {});
    await expect(getSession()).rejects.toBeInstanceOf(SessionVerificationError);
    expect(log).toHaveBeenCalledWith(
      expect.stringContaining(`"status":${status}`),
    );
    expect(JSON.stringify(log.mock.calls)).not.toContain("secret");
    expect(JSON.stringify(log.mock.calls)).not.toContain("test-token");
  },
);

test("network outage renders a controlled view and excludes children in both layouts", async () => {
  vi.spyOn(globalThis, "fetch").mockRejectedValue(
    new TypeError("secret connection details"),
  );
  vi.spyOn(console, "error").mockImplementation(() => {});
  for (const Layout of [PublicLayout, AuthenticatedLayout]) {
    const result = await Layout({ children: "private content" });
    expect(result.type).toBe(
      (await import("@/components/SessionUnavailable")).default,
    );
    expect(result.props).not.toHaveProperty("children");
  }
});

test("malformed successful response cannot establish a session", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}"));
  vi.spyOn(console, "error").mockImplementation(() => {});
  await expect(getSession()).rejects.toBeInstanceOf(SessionVerificationError);
});
