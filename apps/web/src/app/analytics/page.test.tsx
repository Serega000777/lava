import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import AnalyticsPage from "./page";

describe("AnalyticsPage", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("keeps seller analytics private", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 401 }));
    render(<AnalyticsPage />);
    expect(await screen.findByText("Войдите, чтобы увидеть аналитику.")).toBeInTheDocument();
  });
});
