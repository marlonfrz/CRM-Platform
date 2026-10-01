export type ActivityStatus = "PENDING" | "COMPLETED";
export type ActivityView = "TODAY" | "SCHEDULED" | "HISTORY";
export type ActivityDepartment = { id: string; name: string };
export type ActivityCandidate = { id: string; name: string; department_ids: string[] };
export type ActivityTypeOption = { id: string; name: string; department_id: string | null };
export type Activity = {
  id: string;
  client_id: string;
  user_id: string;
  user_name: string;
  assigned_to_user_id: string;
  assigned_to_name: string;
  department_id: string | null;
  department_name: string | null;
  activity_type_id: string;
  activity_type_name: string;
  title: string | null;
  description: string;
  next_action: string | null;
  scheduled_for: string;
  status: ActivityStatus;
  occurred_at: string | null;
  completed_at: string | null;
  schedule_id: string | null;
  created_at: string;
  updated_at: string;
  can_edit: boolean;
  can_delete: boolean;
};
export type ActivityPage = {
  items: Activity[];
  departments: ActivityDepartment[];
  candidates: ActivityCandidate[];
  activity_types: ActivityTypeOption[];
  can_create: boolean;
  can_manage_types: boolean;
  has_more: boolean;
};
export type ActivityFilters = { type: string; department: string; view: ActivityView };

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function parseActivityFilters(
  query: Record<string, string | string[] | undefined>,
): ActivityFilters {
  const type = typeof query.tracking_type === "string" && uuid.test(query.tracking_type)
    ? query.tracking_type : "";
  const department = typeof query.tracking_department === "string"
    && uuid.test(query.tracking_department) ? query.tracking_department : "";
  const rawView = typeof query.tracking_view === "string" ? query.tracking_view : "";
  const view: ActivityView = ["TODAY", "SCHEDULED", "HISTORY"].includes(rawView)
    ? rawView as ActivityView
    : "TODAY";
  return { type, department, view };
}

export function activityQuery(filters: ActivityFilters, offset = 0): string {
  const query = new URLSearchParams({
    period: filters.view,
    offset: String(offset),
    limit: "20",
  });
  if (filters.type) query.set("activity_type_id", filters.type);
  if (filters.department) query.set("department_id", filters.department);
  return query.toString();
}

export function activityPageQuery(filters: ActivityFilters): string {
  const query = new URLSearchParams({ tracking_view: filters.view });
  if (filters.type) query.set("tracking_type", filters.type);
  if (filters.department) query.set("tracking_department", filters.department);
  return query.toString();
}

export function localDateValue(value = new Date()): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function activityDate(value: string): string {
  return new Intl.DateTimeFormat("es-ES", { dateStyle: "medium" }).format(
    new Date(`${value}T12:00:00`),
  );
}

export function activityGroupDate(value: string): string {
  return new Intl.DateTimeFormat("es-ES", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(new Date(`${value}T12:00:00`));
}

function recurrenceBody(data: FormData) {
  const preset = String(data.get("recurrencePreset") ?? "NONE");
  if (preset === "NONE") return null;
  const endsOn = String(data.get("recurrenceEndsOn") ?? "") || null;
  if (preset === "WORKDAYS") {
    return { repeat_unit: "WEEK", repeat_interval: 1, weekdays: [0, 1, 2, 3, 4], ends_on: endsOn };
  }
  if (preset === "DAILY") {
    return { repeat_unit: "DAY", repeat_interval: 1, weekdays: [], ends_on: endsOn };
  }
  const custom = preset === "CUSTOM";
  const unit = custom ? String(data.get("repeatUnit") ?? "DAY") : preset;
  const repeatUnit = unit === "WEEKLY" ? "WEEK" : unit === "MONTHLY" ? "MONTH" : unit;
  const interval = custom ? Number(data.get("repeatInterval") ?? 1) : 1;
  const weekdays = repeatUnit === "WEEK"
    ? data.getAll("weekdays").map(Number)
    : [];
  const monthlyMode = repeatUnit === "MONTH"
    ? String(data.get("monthlyMode") ?? "DAY_OF_MONTH")
    : null;
  return {
    repeat_unit: repeatUnit,
    repeat_interval: interval,
    weekdays,
    monthly_mode: monthlyMode,
    monthly_day: monthlyMode === "DAY_OF_MONTH" ? Number(data.get("monthlyDay") ?? 1) : null,
    monthly_week: monthlyMode === "NTH_WEEKDAY" ? Number(data.get("monthlyWeek") ?? 1) : null,
    monthly_weekday: monthlyMode === "NTH_WEEKDAY"
      ? Number(data.get("monthlyWeekday") ?? 0) : null,
    ends_on: endsOn,
  };
}

export function activityFormBody(data: FormData, editing: boolean) {
  const occurredAt = String(data.get("occurredAt") ?? "");
  const common = {
    activity_type_id: String(data.get("activityTypeId")),
    title: String(data.get("title") ?? "").trim() || null,
    description: String(data.get("description") ?? "").trim(),
    next_action: String(data.get("nextAction") ?? "").trim() || null,
    scheduled_for: String(data.get("scheduledFor") ?? localDateValue()),
    occurred_at: occurredAt ? new Date(occurredAt).toISOString() : null,
    assigned_to_user_id: data.get("assignee") || null,
  };
  if (editing) return common;
  return {
    ...common,
    status: String(data.get("status") ?? "PENDING"),
    department_id: data.get("departmentId") || null,
    recurrence: recurrenceBody(data),
  };
}

export { formatUtcTimestamp as activityTimestamp } from "./date-time";
