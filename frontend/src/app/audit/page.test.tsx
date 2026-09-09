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
  entity_type: "DEPARTMENT", entity_id: "deleted", created_at: "2026-09-09T10:00:00Z",
  metadata: { name: "<script>unsafe</script>", token: "secret-not-rendered" } };

describe("Owner audit page", () => {
  beforeEach(() => {
    vi.mocked(loadWorkspace).mockReset().mockResolvedValue(workspace);
    vi.mocked(serverApi).mockReset().mockResolvedValue({ items: [], has_more: false });
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
  });
  it("preserves filters while paginating", () => {
    const markup = renderToStaticMarkup(<AuditPanel page={{ items: [entry], has_more: true }}
      filters={{ ...filters, offset: 20, action: "DELETED_DEPARTMENT" }} invalidRange={false} />);
    expect(markup).toContain("offset=40&amp;action=DELETED_DEPARTMENT");
    expect(markup).toContain("offset=0&amp;action=DELETED_DEPARTMENT");
  });
  it("validates filters and sends explicit UTC dates to the API", () => {
    expect(parseAuditFilters({ action: "__proto__", offset: "-1", actor_user_id: "bad", since: ["2026-01-01T00:00"] })).toEqual(filters);
    const selected = parseAuditFilters({ action: "AUTH_LOGIN", since: "2026-09-09T10:00", offset: "20" });
    expect(auditQuery(selected, true)).toContain("since=2026-09-09T10%3A00%3A00Z");
    expect(auditQuery(selected)).toContain("since=2026-09-09T10%3A00");
  });
});
