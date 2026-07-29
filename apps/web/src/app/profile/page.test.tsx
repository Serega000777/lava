import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ProfilePage from "./page";

describe("ProfilePage", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows a human-readable verification level", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        display_name: "Мария",
        phone: "+79990000000",
        role: "user",
        verification_level: 2,
      }),
    }));

    render(<ProfilePage />);

    expect(await screen.findByText("Личность проверена")).toBeInTheDocument();
    expect(screen.getByText("Мария")).toBeInTheDocument();
  });
});
