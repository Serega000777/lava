import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ModerationPage from "./page";

describe("ModerationPage", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("loads separate listing, complaint and appeal queues", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async (url: string) => ({
      ok: true,
      json: async () => {
        if (url.includes("/reputation-signals")) {
          return [{
            user_id: "seller-1",
            display_name: "Проверяемый магазин",
            detected: true,
            window_hours: 24,
            review_count: 5,
            distinct_reviewer_count: 3,
            new_account_reviewer_count: 3,
            dominant_rating: 5,
            dominant_rating_count: 5,
            repeat_review_count: 2,
            indicators: ["review_burst", "new_account_cluster", "rating_concentration"],
          }];
        }
        if (url.includes("/review-disputes")) {
          return [{
            id: "review-dispute-1",
            review_id: "review-1",
            reason_code: "abusive",
            details: "В тексте есть оскорбление",
            rating: 1,
            review_comment: "Грубый текст",
            reviewer_name: "Покупатель",
            reviewee_name: "Продавец",
          }];
        }
        if (url.includes("/message-reports")) {
          return [{
            id: "message-report-1",
            message_id: "message-1",
            reported_user_id: "seller-1",
            reason_code: "spam",
            details: "",
            message_body: "Оплатите по ссылке",
            media: [{ id: "evidence-1", width: 32, height: 24 }],
          }];
        }
        if (url.includes("/complaints")) {
          return [{
            id: "complaint-1",
            listing_id: "listing-1",
            reason_code: "fraud",
            details: "Просит предоплату вне платформы",
            status: "open",
            coordination_signal: {
              detected: true,
              window_hours: 24,
              reporter_count: 3,
              dominant_reason_code: "fraud",
              dominant_reason_count: 3,
              new_account_reporter_count: 3,
              indicators: ["reporter_burst", "reason_concentration", "new_account_cluster"],
            },
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
    expect(screen.getByRole("heading", { name: "Сообщения" })).toBeInTheDocument();
    expect(screen.getByText("Оплатите по ссылке")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Вложение из жалобы" }))
      .toHaveAttribute("src", "http://localhost:8000/moderation/message-media/evidence-1");
    expect(screen.getByRole("heading", { name: "Апелляции" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Споры по отзывам" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Сигналы репутации" })).toBeInTheDocument();
    expect(screen.getByText("Проверяемый магазин")).toBeInTheDocument();
    expect(screen.getByText(/не влияют на рейтинг/)).toBeInTheDocument();
    expect(screen.getByText(/всплеск отзывов, группа новых аккаунтов/)).toBeInTheDocument();
    expect(screen.getByText("В тексте есть оскорбление")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Исключить отзыв" })).toBeInTheDocument();
    expect(screen.getByRole("note")).toHaveTextContent("Возможна координация");
  });
});
