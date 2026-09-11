import { searchResponseSchema } from "@lava/api-contracts";
import { describe, expect, it } from "vitest";

describe("shared API contracts", () => {
  it("accepts the current public search wire format", () => {
    const response = searchResponseSchema.parse({
      items: [
        {
          id: "3edb12fe-71ef-4b01-bbf9-e4b45a5d32d4",
          category_id: "266b563a-6d0f-4915-9296-7c9c74180dd6",
          title: "Насос 24В",
          description: "Для перекачки топлива",
          price: "100.00",
          city: "Москва",
          attributes: {},
          ai_generated_fields: [],
          cover_image_url: null,
          seller_id: "808c6234-c4cb-4f44-8869-def7fbbf93e5",
          seller_name: "Магазин оборудования",
          seller_trust_badge: "Новый",
          created_at: "2026-07-27T13:56:39.296282Z",
        },
      ],
      total: 1,
      limit: 5,
      offset: 0,
    });

    expect(response.items[0]?.price).toBe("100.00");
  });
});
