import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ModerationPage from "./page";

describe("ModerationPage", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("loads separate listing, complaint and appeal queues", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async (url: string) => ({
      ok: true,
      json: async () => {
        if (url.includes("/complaints")) {
          return [{
            id: "complaint-1",
            listing_id: "listing-1",
            reason_code: "fraud",
            details: "Просит предоплату вне платформы",
            status: "open",
          }];
        }
        if (url.includes("/appeals")) {
          return [{
            id: "appeal-1",
            case_id: "case-1",
            reason: "В объявлении указаны все обязательные характеристики товара.",
            status: "open",
          }];
        }
        return [];
      },
    })));

    render(<ModerationPage />);

    expect(await screen.findByText("Просит предоплату вне платформы")).toBeInTheDocument();
    expect(screen.getByText("В объявлении указаны все обязательные характеристики товара."))
      .toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Жалобы" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Апелляции" })).toBeInTheDocument();
  });
});
