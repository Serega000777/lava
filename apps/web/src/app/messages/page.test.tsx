import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import MessagesPage from "./page";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
}));

describe("MessagesPage", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("does not expose an inbox to a guest", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 401 }));

    render(<MessagesPage />);

    expect(await screen.findByText("Войдите, чтобы увидеть сообщения.")).toBeInTheDocument();
  });
});
