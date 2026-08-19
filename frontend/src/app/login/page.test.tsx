import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { LoginForm } from "./login-form";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), refresh: vi.fn() }),
}));

describe("LoginPage", () => {
  it("renders the private access form", () => {
    const markup = renderToStaticMarkup(<LoginForm />);

    expect(markup).toContain('type="email"');
    expect(markup).toContain('type="password"');
  });
});
