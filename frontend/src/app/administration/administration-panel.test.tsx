import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { AdministrationPanel } from "./administration-panel";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

describe("AdministrationPanel", () => {
  it("shows owner controls for a business organization", () => {
    const markup = renderToStaticMarkup(
      <AdministrationPanel
        canCreateDepartments
        departments={[{ id: "sales", name: "Ventas" }]}
      />,
    );

    expect(markup).toContain("Nuevo departamento");
    expect(markup).toContain("Ventas");
    expect(markup).toContain("Eliminar");
  });

  it("hides department creation from scoped administrators", () => {
    const markup = renderToStaticMarkup(
      <AdministrationPanel
        canCreateDepartments={false}
        departments={[{ id: "sales", name: "Ventas" }]}
      />,
    );

    expect(markup).not.toContain("Nuevo departamento");
    expect(markup).toContain("Ventas");
  });
});
