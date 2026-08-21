import { describe, expect, it } from "vitest";

import { MobileConfigurationError, readMobileConfig } from "./config";

describe("readMobileConfig", () => {
  it("normalizes a LAN API origin", () => {
    expect(readMobileConfig("http://192.168.1.25:8000/")).toEqual({
      apiOrigin: "http://192.168.1.25:8000",
    });
  });

  it("rejects missing or path-scoped API URLs", () => {
    expect(() => readMobileConfig(undefined)).toThrow(MobileConfigurationError);
    expect(() => readMobileConfig("http://localhost:8000/api")).toThrow(
      "должен содержать только origin",
    );
  });
});
