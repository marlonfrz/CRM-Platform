export type HistoryEntry = {
  id: string;
  client_id: string;
  client_name: string;
  department_id: string | null;
  department_name: string | null;
  person_id: string;
  person_name: string;
  activity_type_id: string;
  activity_type_name: string;
  title: string | null;
  description: string;
  next_action: string | null;
  scheduled_for: string;
  status: "PENDING" | "COMPLETED";
  occurred_at: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  schedule_id: string | null;
  can_edit: boolean;
  can_delete: boolean;
};
export type HistoryPage = { items: HistoryEntry[]; has_more: boolean };
export type Dashboard = {
  metrics: {
    clients: number;
    pending_tasks: number;
    completed_tasks: number;
    activities: number;
    today_clients: number;
    today_activities: number;
    today_pending_tasks: number;
    active_users: number | null;
    departments: number | null;
  };
  departments: {
    id: string;
    name: string;
    active_employees: number;
    activities: number;
    pending_tasks: number;
  }[];
  today_activities: HistoryEntry[];
  recent_activities: HistoryEntry[];
  pending_tasks: HistoryEntry[];
};
