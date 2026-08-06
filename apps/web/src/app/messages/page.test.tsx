import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import MessagesPage from "./page";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
}));

describe("MessagesPage", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("does not expose an inbox to a guest", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 401 }));

    render(<MessagesPage />);

    expect(await screen.findByText("Войдите, чтобы увидеть сообщения.")).toBeInTheDocument();
  });

  it("explains message rate limits without discarding the form", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async (input: string, init?: RequestInit) => {
      if (input.endsWith("/auth/csrf")) return { ok: true, json: async () => ({ token: "csrf" }) };
      if (input.endsWith("/me")) return { ok: true, json: async () => ({ id: "buyer-1" }) };
      if (input.endsWith("/conversations")) {
        return {
          ok: true,
          json: async () => [{
            id: "conversation-1",
            listing_title: "Насос",
            counterpart_id: "seller-1",
            counterpart_name: "Продавец",
          }],
        };
      }
      if (input.includes("/reputation")) return { ok: false };
      if (input.endsWith("/messages") && init?.method === "POST") {
        return { ok: false, status: 429 };
      }
      if (input.endsWith("/messages")) return { ok: true, json: async () => [] };
      throw new Error(`unexpected request: ${input}`);
    }));

    render(<MessagesPage />);
    const textarea = await screen.findByPlaceholderText("Напишите сообщение…");
    fireEvent.change(textarea, { target: { value: "Здравствуйте" } });
    fireEvent.click(screen.getByRole("button", { name: "Отправить" }));

    expect(await screen.findByText(/Слишком много сообщений/)).toBeInTheDocument();
    expect(textarea).toHaveValue("Здравствуйте");
  });
});
