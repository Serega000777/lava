import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import SearchPage from "./page";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams("q=велосипед"),
  useRouter: () => ({ push: vi.fn() }),
}));

describe("SearchPage", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("loads and renders public search results", async () => {
    const fetchMock = vi.fn().mockImplementation(async (url: string) => ({
      ok: true,
      json: async () => url.includes("/favorites") ? [] : ({
        total: 1,
        limit: 24,
        offset: 0,
        items: [{
          id: "listing-1",
          category_id: "category-1",
          title: "Городской велосипед",
          description: "После обслуживания",
          price: "25000.00",
          city: "Москва",
          seller_id: "seller-1",
          seller_name: "ООО Север",
          seller_trust_badge: "Проверенная компания",
          attributes: {},
          created_at: "2026-07-27T00:00:00Z",
        }],
      }),
    }));
    vi.stubGlobal("fetch", fetchMock);

    render(<SearchPage />);

    expect(await screen.findByText("Городской велосипед")).toBeInTheDocument();
    expect(screen.getByText("25 000 ₽")).toBeInTheDocument();
    expect(screen.getByText("Найдено: 1")).toBeInTheDocument();
    expect(screen.getByText("Проверенная компания")).toBeInTheDocument();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("q=%D0%B2%D0%B5%D0%BB%D0%BE%D1%81%D0%B8%D0%BF%D0%B5%D0%B4"),
    ));
  });
});
