import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { api, ApiError } from "../src/lib/api-client";
import { Feedback } from "../src/components/Feedback";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

test("backend envelope reaches customer feedback with request ID and retryability", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: "DATABASE_UNAVAILABLE",
            message: "Service is temporarily unavailable. Please retry.",
            retryable: true,
          },
          request_id: "request-123",
        }),
        { status: 503 },
      ),
    ),
  );
  let error: ApiError | undefined;
  try {
    await api("/orders");
  } catch (caught) {
    error = caught as ApiError;
  }
  expect(error).toBeInstanceOf(ApiError);
  expect(error?.code).toBe("DATABASE_UNAVAILABLE");
  expect(error?.retryable).toBe(true);
  expect(error?.status).toBe(503);
  render(<Feedback error={error!} retry={() => {}} />);
  expect(screen.getByRole("alert")).toHaveTextContent(
    "Service is temporarily unavailable. Please retry.",
  );
  expect(screen.getByText(/Request ID: request-123/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
});
