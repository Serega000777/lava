import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ProfilePage from "./page";

describe("ProfilePage", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows verification and active sessions", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async (url: string) => {
      if (url.includes("/auth/sessions")) return {
        ok: true,
        json: async () => [{
        id: "session-1", created_at: "2026-07-31T10:00:00Z",
        expires_at: "2026-08-31T10:00:00Z", is_current: true,
        }],
      };
      if (url.includes("/reviews")) return { ok: true, json: async () => [] };
      return {
        ok: true,
        json: async () => ({
          id: "user-1", display_name: "Мария", phone: "+79990000000",
          role: "user", verification_level: 2,
        }),
      };
    }));

    render(<ProfilePage />);

    expect(await screen.findByText("Личность проверена")).toBeInTheDocument();
    expect(screen.getByText(/текущий/)).toBeInTheDocument();
    expect(await screen.findByText("Отзывов пока нет.")).toBeInTheDocument();
  });

  it("lets the reviewed user publish one visible reply", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/me")) return {
        ok: true,
        json: async () => ({
          id: "seller-1", display_name: "Продавец", phone: "+79990000000",
          role: "user", verification_level: 1,
        }),
      };
      if (url.includes("/auth/sessions")) return { ok: true, json: async () => [] };
      if (url.endsWith("/users/seller-1/reviews")) return {
        ok: true,
        json: async () => [{
          id: "review-1", reviewer_name: "Покупатель", rating: 5,
          comment: "Всё хорошо", created_at: "2026-09-02T10:00:00Z", reply: null,
        }],
      };
      if (url.endsWith("/auth/csrf")) return {
        ok: true,
        json: async () => ({ token: "csrf-token" }),
      };
      if (url.endsWith("/reviews/review-1/reply") && init?.method === "POST") return {
        ok: true,
        status: 201,
        json: async () => ({ body: "Спасибо", created_at: "2026-09-02T11:00:00Z" }),
      };
      throw new Error(`unexpected request: ${url}`);
    }));

    render(<ProfilePage />);
    const input = await screen.findByLabelText("Ответ на отзыв");
    fireEvent.change(input, { target: { value: "Спасибо" } });
    fireEvent.click(screen.getByRole("button", { name: "Опубликовать ответ" }));

    expect(await screen.findByText("Ответ опубликован.")).toBeInTheDocument();
    expect(screen.getByText("Спасибо")).toBeInTheDocument();
    expect(screen.queryByLabelText("Ответ на отзыв")).not.toBeInTheDocument();
  });
});
