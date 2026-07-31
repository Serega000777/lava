import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ProfilePage from "./page";

describe("ProfilePage", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows verification and active sessions", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async (url: string) => ({
      ok: true,
      json: async () => url.includes("/auth/sessions") ? [{
        id: "session-1", created_at: "2026-07-31T10:00:00Z",
        expires_at: "2026-08-31T10:00:00Z", is_current: true,
      }] : ({
        display_name: "Мария", phone: "+79990000000", role: "user", verification_level: 2,
      }),
    })));

    render(<ProfilePage />);

    expect(await screen.findByText("Личность проверена")).toBeInTheDocument();
    expect(screen.getByText(/текущий/)).toBeInTheDocument();
  });
});
