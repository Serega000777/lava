import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import RecoveryPage from "./page";

describe("RecoveryPage", () => {
  it("starts with a phone recovery form", () => {
    render(<RecoveryPage />);
    expect(screen.getByRole("heading", { name: "Новый пароль" })).toBeInTheDocument();
    expect(screen.getByLabelText("Телефон")).toHaveAttribute("type", "tel");
    expect(screen.getByRole("button", { name: "Получить код" })).toBeInTheDocument();
  });
});
