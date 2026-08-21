import { z } from "zod";
import { describe, expect, it, vi } from "vitest";

import { ApiRequestError, createApiClient, type FetchLike } from "./client";

describe("createApiClient", () => {
  it("validates successful API responses", async () => {
    const fetcher = vi.fn<FetchLike>().mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), { status: 200 }),
    );
    const client = createApiClient("http://192.168.1.25:8000", fetcher);

    await expect(client.get("/health", z.object({ status: z.literal("ok") }))).resolves.toEqual({
      status: "ok",
    });
    expect(fetcher).toHaveBeenCalledWith(
      "http://192.168.1.25:8000/health",
      expect.objectContaining({ headers: { Accept: "application/json" } }),
    );
  });

  it("does not expose an untrusted API error body", async () => {
    const fetcher = vi.fn<FetchLike>().mockResolvedValue(
      new Response(JSON.stringify({ detail: "internal secret" }), { status: 503 }),
    );
    const client = createApiClient("http://192.168.1.25:8000", fetcher);

    await expect(client.get("/health", z.unknown())).rejects.toEqual(
      new ApiRequestError("API вернул ошибку", 503),
    );
  });
});
