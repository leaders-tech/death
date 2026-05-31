/*
This file tests the main app route.
Edit this file when top-level routes change.
Copy a test pattern here when you add another app-level route.
*/

import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";

vi.mock("../pages/GamePage", () => ({
  GamePage: () => <h1>Daemon Arena</h1>,
}));

import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { App } from "./App";

describe("App routes", () => {
  it("shows the game page for every route", () => {
    render(
      <MemoryRouter initialEntries={["/anything"]}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByRole("heading", { name: "Daemon Arena" })).toBeInTheDocument();
  });
});
