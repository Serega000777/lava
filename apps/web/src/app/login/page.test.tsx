import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import LoginPage from "./page";

describe("LoginPage", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("explains the account-level progressive delay", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async (url: string) => {
      if (url.endsWith("/auth/csrf")) {
        return new Response(JSON.stringify({ token: "csrf" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (url.endsWith("/auth/login/password")) {
        return new Response(null, {
          status: 429,
          headers: { "Retry-After": "8" },
        });
      }
      throw new Error(`unexpected request: ${url}`);
    }));

    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("Телефон"), {
      target: { value: "+79990000000" },
    });
    fireEvent.change(screen.getByLabelText("Пароль"), {
      target: { value: "WrongPassword123" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Войти" }).closest("form")!);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Слишком много попыток. Повторите через 8 сек.",
    );
  });
});
