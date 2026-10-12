import React from "react";
import {
  fireEvent,
  render,
  screen,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import CancellationCard from "../src/features/CancellationCard";
import { api, ApiError } from "../src/lib/api-client";
vi.mock("../src/lib/api-client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../src/lib/api-client")>()),
  api: vi.fn(),
}));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});
const action = {
  id: "server-id",
  order_id: "ORD1004",
  product_name: "Keyboard",
  state: "PENDING",
  expires_at: new Date(Date.now() + 300000).toISOString(),
};
test("explicit confirmation uses server action ID", async () => {
  vi.mocked(api).mockResolvedValue({ state: "COMPLETED" });
  render(<CancellationCard action={action} />);
  expect(api).not.toHaveBeenCalled();
  fireEvent.click(screen.getByText("Confirm cancellation"));
  await screen.findByText("Your order is cancelled.");
  expect(api).toHaveBeenCalledWith("/actions/server-id/confirm", {});
});
test("dismiss does not call confirm", async () => {
  vi.mocked(api).mockResolvedValue({ state: "REJECTED" });
  render(<CancellationCard action={action} />);
  fireEvent.click(screen.getByText("Keep order"));
  await waitFor(() =>
    expect(api).toHaveBeenCalledWith("/actions/server-id/dismiss", {}),
  );
});
test("lost response reconciles with same endpoint", async () => {
  vi.mocked(api)
    .mockRejectedValueOnce(new ApiError("Connection interrupted", 0))
    .mockResolvedValueOnce({ state: "COMPLETED" });
  render(<CancellationCard action={action} />);
  fireEvent.click(screen.getByText("Confirm cancellation"));
  fireEvent.click(await screen.findByText("Check cancellation result"));
  await screen.findByText("Your order is cancelled.");
  expect(api).toHaveBeenCalledTimes(2);
});
