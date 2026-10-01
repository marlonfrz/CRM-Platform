import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuditEvent } from "@/components/audit/AuditEvent";
import { AuditPanel } from "@/components/audit/AuditPanel";
import { auditQuery, parseAuditFilters } from "@/lib/audit";
import { loadWorkspace, serverApi, Workspace } from "@/lib/workspace";
import AuditPage from "./page";

vi.mock("@/lib/workspace", () => ({ loadWorkspace: vi.fn(), serverApi: vi.fn() }));
vi.mock("next/navigation", () => ({ redirect: () => { throw new Error("REDIRECT"); }, useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }) }));
const workspace: Workspace = {
  user_id: "owner", user_name: "Owner", user_email: "owner@example.com", user_role: "OWNER",
  organization_name: "Test", organization_mode: "BUSINESS", departments: [],
};
const filters = parseAuditFilters({});
const entry = { id: "event", actor_user_id: null, actor_name: null, action: "DELETED_DEPARTMENT",
  entity_type: "DEPARTMENT", entity_id: "deleted", entity_name: "Diseño",
  created_at: "2026-09-09T10:00:00Z", metadata_names: {},
  metadata: { name: "<script>unsafe</script>", token: "secret-not-rendered" } };

describe("Owner audit page", () => {
  beforeEach(() => {
    vi.mocked(loadWorkspace).mockReset().mockResolvedValue(workspace);
    vi.mocked(serverApi).mockReset().mockResolvedValue({ items: [], actors: [], has_more: false });
  });
  it.each(["ADMIN", "EMPLOYEE"] as const)("rejects %s before querying events", async (role) => {
    vi.mocked(loadWorkspace).mockResolvedValue({ ...workspace, user_role: role });
    await expect(AuditPage({})).rejects.toThrow("REDIRECT");
    expect(serverApi).not.toHaveBeenCalled();
  });
  it.each(["BUSINESS", "INDIVIDUAL"] as const)("supports the %s owner", async (mode) => {
    vi.mocked(loadWorkspace).mockResolvedValue({ ...workspace, organization_mode: mode });
    const markup = renderToStaticMarkup(await AuditPage({}));
    expect(serverApi).toHaveBeenCalledWith("/audit?offset=0", { notFoundOnDenied: true });
    expect(markup).toContain("Auditoría");
    expect(markup).toContain("No hay eventos con estos filtros.");
    expect(markup).not.toContain("Eliminar");
    if (mode === "INDIVIDUAL") expect(markup).not.toContain(">Administración<");
  });
  it("explains invalid ranges without calling the API", async () => {
    const markup = renderToStaticMarkup(await AuditPage({ searchParams: Promise.resolve({ since: "2026-09-10T10:00", until: "2026-09-09T10:00" }) }));
    expect(markup).toContain('role="alert"');
    expect(serverApi).not.toHaveBeenCalled();
  });
  it("escapes names and only displays approved metadata", () => {
    const markup = renderToStaticMarkup(<AuditEvent entry={entry} />);
    expect(markup).toContain("Sistema");
    expect(markup).toContain("Departamento eliminado");
    expect(markup).toContain("&lt;script&gt;");
    expect(markup).not.toContain("secret-not-rendered");
    expect(markup).not.toContain("<script>");
    expect(markup).not.toContain("DELETED_DEPARTMENT");
    expect(markup).not.toContain("ID del autor");
  });
  it("shows human names instead of business identifiers", () => {
    const markup = renderToStaticMarkup(<AuditEvent entry={{
      ...entry,
      actor_user_id: "11111111-1111-1111-1111-111111111111",
      actor_name: "Marta",
      action: "ASSIGNED_CLIENT",
      entity_type: "CLIENT_ASSIGNMENT",
      entity_id: "22222222-2222-2222-2222-222222222222",
      entity_name: "Ana · Hotel Norte",
      metadata: {
        client_id: "33333333-3333-3333-3333-333333333333",
        user_id: "44444444-4444-4444-4444-444444444444",
      },
      metadata_names: { client_id: "Hotel Norte", user_id: "Ana" },
    }} />);
    expect(markup).toContain("Realizado por <strong>Marta</strong>");
    expect(markup).toContain("Ana · Hotel Norte");
    expect(markup).toContain("Hotel Norte");
    expect(markup).not.toContain("33333333-3333-3333-3333-333333333333");
    expect(markup).not.toContain("ASSIGNED_CLIENT");
  });
  it("preserves filters while paginating", () => {
    const markup = renderToStaticMarkup(<AuditPanel page={{
      items: [entry], actors: [{ id: workspace.user_id, name: workspace.user_name }], has_more: true,
    }}
      filters={{ ...filters, offset: 20, action: "DELETED_DEPARTMENT" }} invalidRange={false} />);
    expect(markup).toContain("offset=40&amp;action=DELETED_DEPARTMENT");
    expect(markup).toContain("offset=0&amp;action=DELETED_DEPARTMENT");
    expect(markup).toContain('<option value="owner">Owner</option>');
    expect(markup).toContain("Accesos");
    expect(markup).toContain("Equipo y permisos");
  });
  it("groups audit events under visible date dividers", () => {
    const markup = renderToStaticMarkup(<AuditPanel page={{
      items: [
        entry,
        { ...entry, id: "event-2", created_at: "2026-09-09T08:00:00Z" },
        { ...entry, id: "event-3", created_at: "2026-09-08T18:00:00Z" },
      ],
      actors: [],
      has_more: false,
    }} filters={filters} invalidRange={false} />);
    expect(markup.match(/09\/09\/2026/g)).toHaveLength(1);
    expect(markup).toContain("08/09/2026");
    expect(markup).not.toContain(">Fecha<");
  });
  it("validates filters and sends explicit UTC dates to the API", () => {
    expect(parseAuditFilters({ action: "__proto__", offset: "-1", actor_user_id: "bad", since: ["2026-01-01T00:00"] })).toEqual(filters);
    const selected = parseAuditFilters({ action: "AUTH_LOGIN", since: "2026-09-09T10:00", offset: "20" });
    expect(auditQuery(selected, true)).toContain("since=2026-09-09T10%3A00%3A00Z");
    expect(auditQuery(selected)).toContain("since=2026-09-09T10%3A00");
    const access = parseAuditFilters({ category: "ACCESS", action: "AUTH_LOGIN" });
    expect(auditQuery(access, true)).toContain("category=ACCESS");
    expect(auditQuery(access, true)).toContain("action=AUTH_LOGIN");
    expect(parseAuditFilters({ category: "ACCESS", action: "UPDATED_USER" }).action).toBe("");
    const accessMarkup = renderToStaticMarkup(<AuditPanel page={{
      items: [], actors: [], has_more: false,
    }} filters={access} invalidRange={false} />);
    expect(accessMarkup).toContain("dejar caducar la sesión no registra una salida");
  });
});
