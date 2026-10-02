import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import {
  Activity,
  ActivityPage,
  activityFormBody,
  activityGroupDate,
  activityQuery,
  parseActivityFilters,
} from "@/lib/activities";
import { TrackingPanel } from "@/components/history/TrackingPanel";
import { ActivityOptionsProvider } from "@/components/history/ActivityOptionsStore";

import { ActivityEntry } from "./activity-entry";
import { ActivityForm } from "./activity-form";

vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }) }));

const options: Pick<
  ActivityPage,
  "departments" | "candidates" | "activity_types" | "can_create"
> = {
  departments: [{ id: "10000000-0000-0000-0000-000000000001", name: "Diseño" }],
  candidates: [{
    id: "20000000-0000-0000-0000-000000000001",
    name: "Ana",
    department_ids: ["10000000-0000-0000-0000-000000000001"],
  }],
  activity_types: [{
    id: "30000000-0000-0000-0000-000000000001",
    name: "Llamada",
    department_id: null,
  }],
  can_create: true,
};
const item: Activity = {
  id: "activity", client_id: "client", user_id: "author", user_name: "Ana",
  assigned_to_user_id: options.candidates[0].id, assigned_to_name: "Ana",
  department_id: options.departments[0].id, department_name: "Diseño",
  activity_type_id: options.activity_types[0].id, activity_type_name: "Llamada", type: "CALL",
  title: "Revisar propuesta", description: "Revisamos el formulario.", next_action: null,
  scheduled_for: "2026-09-16", status: "PENDING", occurred_at: null, completed_at: null,
  schedule_id: null, created_at: "2026-09-16T11:00:00Z",
  updated_at: "2026-09-16T11:00:00Z", can_edit: true, can_delete: true,
};

describe("Unified activities", () => {
  it("uses one form for pending and completed activities", () => {
    const markup = renderToStaticMarkup(
      <ActivityOptionsProvider options={options}>
        <ActivityForm clientId="client" onDone={() => {}} />
      </ActivityOptionsProvider>,
    );
    expect(markup).toContain('name="status"');
    expect(markup).toContain('name="scheduledFor"');
    expect(markup).toContain('name="activityTypeId"');
    expect(markup).toContain("Programación");
    expect(markup).toContain("Todos los días laborables");
  });

  it("shows normalized type, date and allowed management actions", () => {
    const markup = renderToStaticMarkup(
      <ActivityEntry clientId="client" activity={item} />,
    );
    expect(markup).toContain("Llamada");
    expect(markup).toContain("Ana · Diseño");
    expect(markup).toContain("Completar");
    expect(markup).toContain("Eliminar");
  });

  it("builds a normalized workday recurrence", () => {
    const data = new FormData();
    data.set("activityTypeId", options.activity_types[0].id);
    data.set("description", " Seguimiento ");
    data.set("scheduledFor", "2026-09-16");
    data.set("status", "PENDING");
    data.set("departmentId", options.departments[0].id);
    data.set("assignee", options.candidates[0].id);
    data.set("recurrencePreset", "WORKDAYS");
    expect(activityFormBody(data, false)).toMatchObject({
      description: "Seguimiento",
      scheduled_for: "2026-09-16",
      recurrence: { repeat_unit: "WEEK", repeat_interval: 1, weekdays: [0, 1, 2, 3, 4] },
    });
  });

  it("validates URL filters and builds a paginated period request", () => {
    const filters = parseActivityFilters({
      tracking_type: options.activity_types[0].id,
      tracking_department: "invalid",
      tracking_view: "SCHEDULED",
    });
    expect(filters).toEqual({
      type: options.activity_types[0].id,
      department: "",
      view: "SCHEDULED",
    });
    expect(activityQuery(filters, 20)).toContain("period=SCHEDULED");
    expect(activityQuery(filters, 20)).toContain("offset=20");
    expect(activityQuery(filters, 20)).toContain("limit=20");
  });

  it("renders one active view grouped by date with incremental loading", () => {
    const second = { ...item, id: "activity-2", title: "Segundo movimiento" };
    const previous = {
      ...item,
      id: "activity-3",
      title: "Movimiento anterior",
      scheduled_for: "2026-09-15",
    };
    const markup = renderToStaticMarkup(
      <TrackingPanel clientId="client" page={{
        ...options,
        items: [item, second, previous],
        can_manage_types: true,
        has_more: true,
      }} filters={{ type: "", department: "", view: "HISTORY" }} />,
    );
    expect(markup).toContain("Hoy");
    expect(markup).toContain("Programadas");
    expect(markup).toContain('aria-current="page"');
    expect(markup).toContain(activityGroupDate("2026-09-16"));
    expect(markup).toContain(activityGroupDate("2026-09-15"));
    expect(markup).toContain("Ver más");
  });
});
