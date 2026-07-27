import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import FavoritesPage from "./page";

describe("FavoritesPage", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows an authentication prompt for guests", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 401 }));

    render(<FavoritesPage />);

    expect(await screen.findByText("Войдите, чтобы увидеть избранное.")).toBeInTheDocument();
  });
});
