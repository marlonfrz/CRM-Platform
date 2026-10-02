import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { DashboardOverview } from "@/components/dashboard/DashboardOverview";
import { HistoryItem } from "@/components/history/HistoryItem";
import { TrackingPanel } from "@/components/history/TrackingPanel";
import type { ActivityPage } from "@/lib/activities";
import type { Workspace } from "@/lib/workspace";

import { Dashboard, HistoryEntry } from "./insights";

vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }) }));

const workspace: Workspace = {
  organization_id: "organization", user_id: "owner", user_name: "Owner", user_email: "owner@example.com", user_role: "OWNER",
  organization_name: "Test", organization_mode: "BUSINESS", departments: [],
};
const entry: HistoryEntry = {
  id: "activity", client_id: "client", client_name: "Hotel",
  department_id: null, department_name: null, person_id: "employee", person_name: "Employee",
  activity_type_id: "type", activity_type_name: "Llamada", title: "Llamar al cliente",
  description: "<script>alert(1)</script>", next_action: null, scheduled_for: "2026-09-16",
  status: "COMPLETED", occurred_at: "2026-09-16T10:00:00Z",
  created_at: "2026-09-16T09:00:00Z", updated_at: "2026-09-16T10:00:00Z",
  completed_at: "2026-09-16T10:00:00Z", schedule_id: null,
  can_edit: false, can_delete: false,
};
const data: Dashboard = {
  metrics: { clients: 2, pending_tasks: 0, completed_tasks: 1, activities: 1,
    today_clients: 1, today_activities: 1, today_pending_tasks: 0, active_users: 3, departments: 1 },
  departments: [{ id: "department", name: "Support", active_employees: 1, activities: 1, pending_tasks: 0 }],
  today_activities: [entry], recent_activities: [], pending_tasks: [],
};
const page: ActivityPage = {
  items: [], departments: [], candidates: [], activity_types: [],
  can_create: false, can_manage_types: false, has_more: false,
};

describe("Dashboard presentation", () => {
  it.each(["OWNER", "ADMIN"] as const)("shows management summaries for %s", (role) => {
    const markup = renderToStaticMarkup(
      <DashboardOverview data={data} workspace={{ ...workspace, user_role: role }} />,
    );
    expect(markup).toContain("Clientes con actividad hoy");
    expect(markup).toContain("Completadas hoy");
    expect(markup).toContain("1 empleado activo");
    expect(markup).toContain("1 actividad hoy");
    expect(markup).toContain("Support");
    expect(markup).toContain("Actividad de hoy");
    expect(markup).toContain("Llamar al cliente");
  });

  it("renders a unified history item and escapes its description", () => {
    const markup = renderToStaticMarkup(<HistoryItem entry={entry} showClient />);
    expect(markup).toContain("Completada");
    expect(markup).toContain("Responsable: Employee");
    expect(markup).toContain('href="/clients/client#tracking"');
    expect(markup).toContain("&lt;script&gt;");
    expect(markup).not.toContain("<script>");
  });

  it("uses one date-filtered tracking timeline", () => {
    const markup = renderToStaticMarkup(
      <TrackingPanel clientId="client" page={{ ...page, items: [] }}
        filters={{ type: "", department: "", view: "TODAY" }} />,
    );
    expect(markup).toContain("Hoy");
    expect(markup).toContain("Programadas");
    expect(markup).toContain("Historial");
    expect(markup).toContain("No hay actividad para hoy");
  });
});
