import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { Activity, activityFormBody, activityQuery, parseActivityFilters } from "@/lib/activities";
import { ActivityForm } from "./activity-form";
import { ActivityEntry } from "./activity-entry";
import { ClientActivities } from "./client-activities";

vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }) }));
const item: Activity = {
  id: "activity", user_id: "author", user_name: "Ana", department_id: "a", department_name: "Informática",
  type: "CALL", description: "Revisamos el formulario.\nSegunda línea.", next_action: "Comprobar mañana",
  occurred_at: "2026-09-07T10:00:00Z", created_at: "2026-09-07T11:00:00Z", updated_at: "2026-09-07T11:00:00Z", can_edit: true,
};
const departments = [{ id: "a", name: "Informática" }, { id: "b", name: "Marketing" }];

describe("Activities", () => {
  it("does not request a department in individual mode or for a single membership", () => {
    for (const choices of [[], departments.slice(0, 1)]) {
      const markup = renderToStaticMarkup(<ActivityForm clientId="client" departments={choices} onDone={() => {}} />);
      expect(markup).not.toContain('name="departmentId"');
      expect(markup).toContain("Descripción");
      expect(markup).toContain("Próxima acción (opcional)");
      expect(markup).toContain("(UTC)");
    }
  });

  it("requires a choice when multiple departments are available", () => {
    const markup = renderToStaticMarkup(<ActivityForm clientId="client" departments={departments} onDone={() => {}} />);
    expect(markup).toContain('name="departmentId" required=""');
    expect(markup).toContain("Informática");
    expect(markup).toContain("Marketing");
  });

  it("corrections do not offer author or department changes", () => {
    const markup = renderToStaticMarkup(<ActivityForm clientId="client" departments={departments} activity={item} onDone={() => {}} />);
    expect(markup).not.toContain('name="departmentId"');
    expect(markup).not.toContain('name="userId"');
    expect(markup).toContain("Guardar corrección");
  });

  it("shows actor, department, dates and correction only when allowed", () => {
    const markup = renderToStaticMarkup(<ActivityEntry clientId="client" activity={item} />);
    expect(markup).toContain("Ana · Informática");
    expect(markup).toContain("Llamada");
    expect(markup).toContain("Comprobar mañana");
    expect(markup).toContain("Corregir actividad");
    const readonly = renderToStaticMarkup(<ActivityEntry clientId="client" activity={{ ...item, can_edit: false, department_name: null }} />);
    expect(readonly).not.toContain("Corregir actividad");
    expect(readonly).not.toContain("Eliminar");
    expect(readonly).not.toContain("Informática");
  });

  it("renders empty state, creation permissions and pagination preserving filters", () => {
    const markup = renderToStaticMarkup(<ClientActivities clientId="client"
      page={{ items: [], departments: [], can_create: false, has_more: true }}
      filters={{ type: "CALL", department: "", offset: 20 }} />);
    expect(markup).not.toContain("Nueva actividad");
    expect(markup).toContain("No hay actividades visibles");
    expect(markup).toContain("activity_type=CALL&amp;offset=40#activities");
    expect(markup).toContain("activity_type=CALL&amp;offset=0#activities");
  });

  it("individual mode exposes creation without department controls", () => {
    const markup = renderToStaticMarkup(<ClientActivities clientId="client"
      page={{ items: [], departments: [], can_create: true, has_more: false }}
      filters={{ type: "", department: "", offset: 0 }} />);
    expect(markup).toContain("Nueva actividad");
    expect(markup).not.toContain('name="department_id"');
    expect(markup).not.toContain("Necesitas pertenecer");
  });

  it("normalizes invalid query values and keeps valid filters", () => {
    expect(parseActivityFilters({ activity_type: "constructor", department_id: "invalid", offset: "-1" }))
      .toEqual({ type: "", department: "", offset: 0 });
    expect(parseActivityFilters({ offset: ["20"], activity_type: ["NOTE"] }).offset).toBe(0);
    expect(activityQuery(parseActivityFilters({ activity_type: "NOTE", offset: "20" })))
      .toBe("activity_type=NOTE&offset=20");
  });

  it("builds UTC requests without letting corrections change attribution", () => {
    const data = new FormData();
    data.set("type", "NOTE"); data.set("description", "  Note  ");
    data.set("occurredAt", "2026-09-07T10:30"); data.set("departmentId", "a");
    const request = activityFormBody(data, false);
    expect(request).toMatchObject({ department_id: "a", occurred_at: "2026-09-07T10:30:00.000Z", description: "Note", next_action: null });
    expect(activityFormBody(data, true)).not.toHaveProperty("department_id");
  });
});
