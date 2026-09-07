export const activityTypes = {
  CALL: "Llamada", EMAIL: "Email", MEETING: "Reunión",
  NOTE: "Nota", INCIDENT: "Incidencia", OTHER: "Otro",
} as const;

export type ActivityType = keyof typeof activityTypes;
export type ActivityDepartment = { id: string; name: string };
export type Activity = {
  id: string; user_id: string; user_name: string;
  department_id: string | null; department_name: string | null;
  type: ActivityType; description: string; next_action: string | null;
  occurred_at: string; created_at: string; updated_at: string; can_edit: boolean;
};
export type ActivityPage = {
  items: Activity[]; departments: ActivityDepartment[]; can_create: boolean; has_more: boolean;
};
export type ActivityFilters = { type: string; department: string; offset: number };

export function parseActivityFilters(query: Record<string, string | string[] | undefined>): ActivityFilters {
  const type = typeof query.activity_type === "string" && Object.hasOwn(activityTypes, query.activity_type)
    ? query.activity_type : "";
  const department = typeof query.department_id === "string"
    && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(query.department_id)
    ? query.department_id : "";
  const rawOffset = typeof query.offset === "string" ? Number(query.offset) : 0;
  const offset = Number.isInteger(rawOffset) && rawOffset >= 0 && rawOffset <= 100000 ? rawOffset : 0;
  return { type, department, offset };
}

export function activityQuery(filters: ActivityFilters): string {
  const query = new URLSearchParams();
  if (filters.type) query.set("activity_type", filters.type);
  if (filters.department) query.set("department_id", filters.department);
  query.set("offset", String(filters.offset));
  return query.toString();
}

export const activityTypeOptions = Object.entries(activityTypes).map(([value, label]) => ({ value, label }));

export { formatUtcTimestamp as activityTimestamp } from "./date-time";

export function activityFormBody(data: FormData, editing: boolean) {
  const date = String(data.get("occurredAt") ?? "");
  const body = {
    type: String(data.get("type")), description: String(data.get("description") ?? "").trim(),
    next_action: String(data.get("nextAction") ?? "").trim() || null,
    occurred_at: date ? new Date(`${date}Z`).toISOString() : new Date().toISOString(),
  };
  return editing ? body : { ...body, department_id: data.get("departmentId") || null };
}
