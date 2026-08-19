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
        canEditOrganization
        departments={[{ id: "sales", name: "Ventas" }]}
        organization={{ name: "Ticket4U", mode: "BUSINESS" }}
      />,
    );

    expect(markup).toContain("Ticket4U");
    expect(markup).toContain("Nuevo departamento");
    expect(markup).toContain("Ventas");
    expect(markup).toContain("Eliminar");
  });

  it("omits departments in individual mode", () => {
    const markup = renderToStaticMarkup(
      <AdministrationPanel
        canCreateDepartments={false}
        canEditOrganization
        departments={[]}
        organization={{ name: "Personal", mode: "INDIVIDUAL" }}
      />,
    );

    expect(markup).not.toContain("Nuevo departamento");
  });
});
