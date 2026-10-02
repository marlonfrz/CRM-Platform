import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { ClientDetailPanel } from "./client-detail-panel";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

const client = {
  id: "client-id",
  name: "Cliente Alfa",
  address: "Calle Ejemplo",
  notes: "Cliente principal",
  created_at: "2026-09-03T10:00:00Z",
  updated_at: "2026-09-03T10:00:00Z",
  contacts: [
    {
      id: "contact-id",
      full_name: "Ana Pérez",
      position: "Gerencia",
      email: "ana@example.com",
      phone: "+34 600 000 000",
      notes: null,
      created_at: "2026-09-03T10:00:00Z",
      updated_at: "2026-09-03T10:00:00Z",
    },
  ],
};

describe("ClientDetailPanel", () => {
  it("shows the client and contact management controls", () => {
    const markup = renderToStaticMarkup(<ClientDetailPanel client={client} canManage />);

    expect(markup).toContain("Cliente Alfa");
    expect(markup).toContain("Ana Pérez");
    expect(markup).toContain("Añadir contacto");
    expect(markup).toContain("Eliminar");
  });

  it("hides mutations in read-only mode", () => {
    const markup = renderToStaticMarkup(
      <ClientDetailPanel client={client} canManage={false} />,
    );

    expect(markup).not.toContain("Añadir contacto");
    expect(markup).not.toContain("Eliminar");
    expect(markup).toContain("ana@example.com");
  });
});
