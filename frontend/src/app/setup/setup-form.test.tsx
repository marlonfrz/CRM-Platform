import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { SetupForm } from "./setup-form";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), refresh: vi.fn() }),
}));

describe("SetupForm", () => {
  it("requires password confirmation and offers visibility control", () => {
    const markup = renderToStaticMarkup(<SetupForm />);

    expect(markup).toContain('name="ownerPassword"');
    expect(markup).toContain('name="ownerPasswordConfirmation"');
    expect(markup).toContain("Mostrar contraseñas");
  });
});
