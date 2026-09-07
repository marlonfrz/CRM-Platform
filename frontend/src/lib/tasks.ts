export type TaskStatus = "PENDING" | "COMPLETED";
export type Task = {
  id: string; client_id: string; client_name: string; title: string; description: string | null;
  assigned_to_user_id: string; assigned_to_name: string; created_by_user_id: string;
  department_id: string | null; department_name: string | null;
  due_at: string | null; status: TaskStatus; completed_at: string | null;
  created_at: string; updated_at: string;
};
export type TaskOptions = {
  individual: boolean; departments: { id: string; name: string }[];
  candidates: { id: string; name: string; department_ids: string[] }[];
};
export type TaskPage = { items: Task[]; has_more: boolean; options: TaskOptions | null };
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
    due_at: date ? new Date(`${date}Z`).toISOString() : null,
    assigned_to_user_id: data.get("assignee") || null,
  };
  return editing ? values : { ...values, department_id: data.get("department") || null };
}
