import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { DashboardOverview } from "@/components/dashboard/DashboardOverview";
import { HistoryItem } from "@/components/history/HistoryItem";
import { HistoryPanel } from "@/components/history/HistoryPanel";
import type { Workspace } from "@/lib/workspace";
import { Dashboard, HistoryEntry, historyApiQuery, historyPageQuery, parseHistoryFilters } from "./insights";

const workspace: Workspace = {
  user_id: "owner", user_name: "Owner", user_email: "owner@example.com", user_role: "OWNER",
  organization_name: "Test", organization_mode: "BUSINESS", departments: [],
};
const entry: HistoryEntry = {
  id: "task", kind: "TASK", client_id: "client", client_name: "Hotel",
  department_id: null, department_name: null, person_id: "employee", person_name: "Employee",
  type: "COMPLETED", title: "Call customer", description: "<script>alert(1)</script>",
  next_action: null, occurred_at: "2026-09-09T10:00:00Z", due_at: null,
};
const data: Dashboard = {
  metrics: { clients: 2, pending_tasks: 0, completed_tasks: 1, activities: 0, active_users: 3, departments: 1 },
  departments: [{ id: "department", name: "Support", active_employees: 2, activities: 0, pending_tasks: 0 }],
  recent_activities: [], pending_tasks: [],
};

describe("Dashboard presentation", () => {
  it.each(["OWNER", "ADMIN"] as const)("shows authorized management summaries for %s", (role) => {
    const markup = renderToStaticMarkup(<DashboardOverview data={data} workspace={{ ...workspace, user_role: role }} />);
    expect(markup).toContain("Clientes del catálogo global");
    expect(markup).toContain(role === "OWNER" ? "Usuarios activos" : "Empleados activos de tu equipo");
    expect(markup).toContain("Support");
    expect(markup).toContain("No hay tareas pendientes en tu alcance.");
    expect(markup).toContain("Todavía no hay actividad visible.");
  });

  it.each([
    { ...workspace, user_role: "EMPLOYEE" as const },
    { ...workspace, organization_mode: "INDIVIDUAL" as const },
  ])("omits hierarchy for $user_role in $organization_mode", (context) => {
    const markup = renderToStaticMarkup(<DashboardOverview data={data} workspace={context} />);
    expect(markup).toContain("Mis clientes");
    expect(markup).toContain("Mis tareas pendientes");
    expect(markup).not.toContain("Departamentos");
    expect(markup).not.toContain("Support");
    expect(markup).not.toContain("Usuarios activos");
  });
});

describe("Client history", () => {
  it("identifies task responsibility without claiming who completed it and escapes text", () => {
    const markup = renderToStaticMarkup(<HistoryItem entry={entry} showClient />);
    expect(markup).toContain("Tarea completada");
    expect(markup).toContain("Responsable: Employee");
    expect(markup).not.toContain("Autor:");
    expect(markup).not.toContain("null");
    expect(markup).toContain("Sin fecha límite");
    expect(markup).toContain('href="/clients/client#tasks"');
    expect(markup).toContain("&lt;script&gt;");
    expect(markup).not.toContain("<script>");
  });

  it("shows activity authorship, department and next action", () => {
    const markup = renderToStaticMarkup(<HistoryItem entry={{ ...entry, kind: "ACTIVITY", type: "CALL",
      department_name: "Support", next_action: "Follow up" }} showClient />);
    expect(markup).toContain("Autor: Employee · Support");
    expect(markup).toContain("Follow up");
    expect(markup).toContain('href="/clients/client#activities"');
    expect(markup).not.toContain("Sin fecha límite");
  });

  it("paginates independently while preserving activity and task filters", () => {
    const markup = renderToStaticMarkup(<HistoryPanel clientId="client" page={{ items: [entry], has_more: true }}
      filters={{ kind: "TASK", offset: 20 }} preservedQuery="type=CALL&task_status=PENDING" />);
    expect(markup).toContain("history_offset=0#history");
    expect(markup).toContain("history_offset=40#history");
    expect(markup).toContain('name="task_status" value="PENDING"');
    expect(markup).toContain('name="type" value="CALL"');
    expect(markup).toContain("No es un registro de cada cambio.");
  });

  it("explains an empty history without pagination", () => {
    const markup = renderToStaticMarkup(<HistoryPanel clientId="client" page={{ items: [], has_more: false }}
      filters={{ kind: "", offset: 0 }} />);
    expect(markup).toContain("No hay registros visibles con este filtro.");
    expect(markup).not.toContain("Páginas del historial");
  });

  it("validates URL filters and uses independent API parameters", () => {
    expect(parseHistoryFilters({ history_kind: "TASK", history_offset: "20" })).toEqual({ kind: "TASK", offset: 20 });
    for (const offset of ["-1", "1.5", "100001", "NaN", ["20"]]) {
      expect(parseHistoryFilters({ history_kind: ["TASK"], history_offset: offset })).toEqual({ kind: "", offset: 0 });
    }
    expect(historyApiQuery({ kind: "ACTIVITY", offset: 20 })).toBe("offset=20&kind=ACTIVITY");
    expect(historyPageQuery({ kind: "TASK", offset: 40 }, "task_status=PENDING&history_offset=20"))
      .toBe("task_status=PENDING&history_offset=40&history_kind=TASK");
  });
});
