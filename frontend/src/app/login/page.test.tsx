import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import LoginPage from "./page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), refresh: vi.fn() }),
}));

describe("LoginPage", () => {
  it("renders the private access form", () => {
    const markup = renderToStaticMarkup(<LoginPage />);

    expect(markup).toContain("Inicia sesión");
    expect(markup).toContain('type="email"');
    expect(markup).toContain('type="password"');
  });
});
