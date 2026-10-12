import React from "react";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import Chat from "../src/features/Chat";
import { api, ApiError } from "../src/lib/api-client";
vi.mock("../src/lib/api-client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../src/lib/api-client")>()),
  api: vi.fn(),
}));
afterEach(() => {
  cleanup();
  sessionStorage.clear();
  vi.resetAllMocks();
});
test("failed send preserves text and retry client ID", async () => {
  sessionStorage.setItem("conversation_id", "conversation");
  vi.mocked(api)
    .mockResolvedValueOnce({ items: [], next_cursor: null })
    .mockRejectedValueOnce(new ApiError("Please retry.", 503))
    .mockResolvedValueOnce({
      message: {
        id: "answer",
        role: "assistant",
        content: "ORD1001 is SHIPPED",
        created_at: new Date().toISOString(),
      },
      action: null,
    });
  render(<Chat />);
  await screen.findByText("Hello. How can we help?");
  const composer = screen.getByLabelText("Message the support assistant");
  fireEvent.change(composer, { target: { value: "Where is ORD1001?" } });
  fireEvent.click(screen.getByRole("button", { name: "Send ↑" }));
  await screen.findByText("Please retry.");
  expect(composer).toHaveValue("Where is ORD1001?");
  fireEvent.click(screen.getByRole("button", { name: "Try again" }));
  await screen.findByText("ORD1001 is SHIPPED");
  const calls = vi
    .mocked(api)
    .mock.calls.filter((call) => call[0] === "/chat/messages");
  expect(calls[0][1]).toEqual(calls[1][1]);
  expect(composer).toHaveValue("");
});
test("only one send runs while provider response is pending", async () => {
  sessionStorage.setItem("conversation_id", "conversation");
  let complete: (value: unknown) => void = () => {};
  vi.mocked(api)
    .mockResolvedValueOnce({ items: [], next_cursor: null })
    .mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          complete = resolve;
        }),
    );
  render(<Chat />);
  await screen.findByText("Hello. How can we help?");
  fireEvent.change(screen.getByLabelText("Message the support assistant"), {
    target: { value: "Where is ORD1001?" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Send ↑" }));
  expect(screen.getByRole("button", { name: "Sending…" })).toBeDisabled();
  expect(
    vi.mocked(api).mock.calls.filter((call) => call[0] === "/chat/messages"),
  ).toHaveLength(1);
  await act(async () =>
    complete({
      message: {
        id: "answer",
        role: "assistant",
        content: "SHIPPED",
        created_at: new Date().toISOString(),
      },
      action: null,
    }),
  );
  await waitFor(() =>
    expect(screen.getByLabelText("Message the support assistant")).toHaveValue(
      "",
    ),
  );
});

test("replaying a restored pending turn does not duplicate its saved assistant", async () => {
  sessionStorage.setItem("conversation_id", "conversation");
  const pending = { id: "client-id", text: "Where is ORD1001?" };
  sessionStorage.setItem("pending:conversation", JSON.stringify(pending));
  const answer = {
    id: "answer",
    role: "assistant",
    content: "ORD1001 is SHIPPED",
    created_at: new Date().toISOString(),
  };
  vi.mocked(api)
    .mockResolvedValueOnce({
      items: [
        {
          id: "user",
          role: "user",
          client_message_id: pending.id,
          content: pending.text,
          created_at: answer.created_at,
        },
        answer,
      ],
      next_cursor: null,
    })
    .mockResolvedValueOnce({ message: answer, action: null });
  render(<Chat />);
  await screen.findByText(answer.content);
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Send ↑" })).toBeEnabled(),
  );
  fireEvent.click(screen.getByRole("button", { name: "Send ↑" }));
  await waitFor(() =>
    expect(screen.getByLabelText("Message the support assistant")).toHaveValue(
      "",
    ),
  );
  expect(screen.getAllByText(answer.content)).toHaveLength(1);
  expect(screen.getAllByText(pending.text)).toHaveLength(1);
});
