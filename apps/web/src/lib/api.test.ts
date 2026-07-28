import { afterEach, describe, expect, it, vi } from "vitest";
import { apiFetch } from "./api";

describe("apiFetch", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("bootstraps and sends a CSRF token for mutations", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ token: "csrf-token" }) })
      .mockResolvedValueOnce({ ok: true, status: 204 });
    vi.stubGlobal("fetch", fetchMock);

    await apiFetch("http://localhost:8000/favorites/listing", { method: "DELETE" });

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "http://localhost:8000/auth/csrf",
      { credentials: "include" },
    );
    const mutation = fetchMock.mock.calls[1]!;
    const init = mutation[1] as RequestInit;
    expect((init.headers as Headers).get("X-CSRF-Token")).toBe("csrf-token");
    expect(init.credentials).toBe("include");
  });
});
