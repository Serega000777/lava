import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Home from "./page";

describe("Home", () => {
  it("shows the initial marketplace categories", () => {
    render(<Home />);
    expect(screen.getByText("Автомобили")).toBeInTheDocument();
    expect(screen.getByText("Товары")).toBeInTheDocument();
    expect(screen.getByText("Услуги")).toBeInTheDocument();
    expect(screen.getByRole("search")).toHaveAttribute("action", "/search");
    expect(screen.getByLabelText("Поиск объявлений")).toHaveAttribute("name", "q");
  });
});
