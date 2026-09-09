export type HistoryEntry = {
  id: string; kind: "ACTIVITY" | "TASK"; client_id: string; client_name: string;
  department_id: string | null; department_name: string | null;
  person_id: string; person_name: string; type: string; title: string;
  description: string | null; next_action: string | null; occurred_at: string; due_at: string | null;
};
export type HistoryPage = { items: HistoryEntry[]; has_more: boolean };
export type HistoryFilters = { kind: string; offset: number };
export type Dashboard = {
  metrics: { clients: number; pending_tasks: number; completed_tasks: number; activities: number; active_users: number | null; departments: number | null };
  departments: { id: string; name: string; active_employees: number; activities: number; pending_tasks: number }[];
  recent_activities: HistoryEntry[]; pending_tasks: HistoryEntry[];
};

export function parseHistoryFilters(query: Record<string, string | string[] | undefined>): HistoryFilters {
  const kind = query.history_kind === "ACTIVITY" || query.history_kind === "TASK" ? query.history_kind : "";
  const raw = typeof query.history_offset === "string" ? Number(query.history_offset) : 0;
  return { kind, offset: Number.isInteger(raw) && raw >= 0 && raw <= 100000 ? raw : 0 };
}

export function historyApiQuery(filters: HistoryFilters) {
  const query = new URLSearchParams({ offset: String(filters.offset) });
  if (filters.kind) query.set("kind", filters.kind);
  return query.toString();
}

export function historyPageQuery(filters: HistoryFilters, preserved = "") {
  const query = new URLSearchParams(preserved);
  query.set("history_kind", filters.kind); query.set("history_offset", String(filters.offset));
  return query.toString();
}
