import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Workspace } from "@/lib/workspace";
import { loadWorkspace, serverApi } from "@/lib/workspace";
import { ClientAssignments } from "./client-assignments";
import ClientPage from "./page";

vi.mock("@/lib/workspace", () => ({ loadWorkspace: vi.fn(), serverApi: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }),
  notFound: () => { throw new Error("NOT_FOUND"); },
}));

const clientId = "42e62f7d-b1ee-4a44-a917-0a060c44b923";
const client = {
  id: clientId, name: "Test Hotel", address: null, notes: null,
  created_at: "2026-09-07T10:00:00Z", updated_at: "2026-09-07T10:00:00Z", contacts: [],
};
const workspace: Workspace = {
  user_id: "owner", user_name: "Owner", user_email: "owner@example.com", user_role: "OWNER",
  organization_name: "Test", organization_mode: "BUSINESS", departments: [],
};

describe("Assignment access in the client page", () => {
  beforeEach(() => {
    vi.mocked(loadWorkspace).mockReset();
    vi.mocked(serverApi).mockReset();
    vi.mocked(serverApi).mockResolvedValue({ items: [], departments: [], can_create: false, has_more: false });
  });

  it.each(["OWNER", "ADMIN"] as const)("loads the team for a business %s", async (role) => {
    vi.mocked(loadWorkspace).mockResolvedValue({ ...workspace, user_role: role });
    vi.mocked(serverApi).mockResolvedValueOnce(client).mockResolvedValueOnce({ assigned: [], available: [] });
    const markup = renderToStaticMarkup(await ClientPage({ params: Promise.resolve({ clientId }) }));
    expect(serverApi).toHaveBeenCalledWith(`/clients/${clientId}/assignments`, { notFoundOnDenied: true });
    expect(markup).toContain("Equipo asignado");
    expect(markup).toContain("No hay empleados disponibles");
    expect(markup).toContain(`href="/summaries?client_id=${clientId}"`);
    expect(markup).toContain("Generar resumen de actividad con IA");
  });

  it("lets an assigned employee read the client without management controls", async () => {
    vi.mocked(loadWorkspace).mockResolvedValue({ ...workspace, user_role: "EMPLOYEE" });
    vi.mocked(serverApi).mockResolvedValueOnce(client);
    const markup = renderToStaticMarkup(await ClientPage({ params: Promise.resolve({ clientId }) }));
    expect(serverApi).toHaveBeenCalledTimes(2);
    expect(markup).toContain("Mis clientes");
    expect(markup).toContain("Test Hotel");
    expect(markup).not.toContain("Equipo asignado");
    expect(markup).not.toContain("Añadir contacto");
    expect(markup).not.toContain("Generar resumen de actividad con IA");
    expect(markup).not.toContain(">Editar<");
  });

  it("omits all assignment UI and requests for the individual owner", async () => {
    vi.mocked(loadWorkspace).mockResolvedValue({ ...workspace, organization_mode: "INDIVIDUAL" });
    vi.mocked(serverApi).mockResolvedValueOnce(client);
    const markup = renderToStaticMarkup(await ClientPage({ params: Promise.resolve({ clientId }) }));
    expect(serverApi).toHaveBeenCalledTimes(2);
    expect(markup).not.toContain("Equipo asignado");
    expect(markup).toContain("Añadir contacto");
  });

  it("does not render stale client information after access has been removed", async () => {
    vi.mocked(loadWorkspace).mockResolvedValue({ ...workspace, user_role: "EMPLOYEE" });
    vi.mocked(serverApi).mockRejectedValue(new Error("NOT_FOUND"));
    await expect(ClientPage({ params: Promise.resolve({ clientId }) })).rejects.toThrow("NOT_FOUND");
    expect(serverApi).toHaveBeenCalledWith(`/clients/${clientId}`, { notFoundOnDenied: true });
  });

  it("only offers available employees and keeps disabled assignments removable", () => {
    const markup = renderToStaticMarkup(<ClientAssignments clientId={clientId} scoped team={{
      assigned: [{ user_id: "disabled", full_name: "Disabled Employee", status: "DISABLED" }],
      available: [{ user_id: "active", full_name: "Available Employee", status: "ACTIVE" }],
    }} />);
    expect(markup).toContain('<option value="active">Available Employee</option>');
    expect(markup).not.toContain('<option value="disabled">');
    expect(markup).toContain("Desactivado");
    expect(markup).toContain("Retirar asignación de Disabled Employee");
  });
});
