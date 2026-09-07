import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { ClientCreateForm } from "./client-create-form";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

describe("ClientCreateForm", () => {
  it("renders only the fields defined for the client MVP", () => {
    const markup = renderToStaticMarkup(<ClientCreateForm />);

    expect(markup).toContain("Nuevo cliente");
    expect(markup).toContain("Nombre");
    expect(markup).toContain("Dirección");
    expect(markup).toContain("Notas");
    expect(markup).not.toContain("Departamento");
  });
});
