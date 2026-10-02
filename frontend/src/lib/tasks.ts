import type { ActivityStatus, TaskOptions as ApiTaskOptions, TaskPage as ApiTaskPage, TaskResponse } from "@/lib/api-generated";

export type TaskStatus = ActivityStatus;
export type Task = TaskResponse;
export type TaskOptions = ApiTaskOptions;
export type TaskPage = ApiTaskPage;
export type TaskFilters = { status: string; offset: number };
export const taskStatusOptions = [
  { value: "", label: "Todos los estados" },
  { value: "PENDING", label: "Pendientes" },
  { value: "COMPLETED", label: "Completadas" },
];

export function parseTaskFilters(query: Record<string, string | string[] | undefined>): TaskFilters {
  const status = query.task_status === "PENDING" || query.task_status === "COMPLETED" ? query.task_status : "";
  const raw = typeof query.task_offset === "string" ? Number(query.task_offset) : 0;
  return { status, offset: Number.isInteger(raw) && raw >= 0 && raw <= 100000 ? raw : 0 };
}

export function taskApiQuery(filters: TaskFilters) {
  const query = new URLSearchParams({ offset: String(filters.offset) });
  if (filters.status) query.set("status", filters.status);
  return query.toString();
}

export function taskPageQuery(filters: TaskFilters, preserved = "") {
  const query = new URLSearchParams(preserved);
  query.set("task_offset", String(filters.offset));
  query.set("task_status", filters.status);
  return query.toString();
}

export function taskFormBody(data: FormData, editing: boolean) {
  const date = String(data.get("dueAt") ?? "");
  const values = {
    title: String(data.get("title") ?? "").trim(),
    description: String(data.get("description") ?? "").trim() || null,
    due_at: date ? `${date}T12:00:00Z` : null,
    assigned_to_user_id: data.get("assignee") || null,
  };
  return editing ? values : { ...values, department_id: data.get("department") || null };
}
