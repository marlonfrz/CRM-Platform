import { randomUUID } from "node:crypto";
import type { Activity, ActivityPage } from "@/lib/activities";
import type { AuditEntry, AuditPage } from "@/lib/audit";
import type { AssignmentTeam, Client, ClientContact, ClientSummary } from "@/lib/clients";
import type { Dashboard, HistoryEntry, HistoryPage } from "@/lib/insights";
import type { AIConfiguration, SummaryLatest, SummaryOptions, SummaryResult } from "@/lib/summaries";
import type { Task, TaskPage } from "@/lib/tasks";
import type { Workspace } from "@/lib/workspace";

type Department = { id: string; name: string };
type DemoUser = { id: string; email: string; full_name: string; role: Workspace["user_role"]; status: "PENDING" | "ACTIVE" | "DISABLED"; department_ids: string[] };
type DemoClient = Client & { assigned_user_ids: string[] };
type DemoState = { clients: DemoClient[]; users: DemoUser[]; departments: Department[]; activities: Activity[]; types: { id: string; name: string; department_id: string | null }[]; audit: AuditEntry[]; summaries: SummaryLatest[]; aiConfiguration: AIConfiguration };

const ids = {
  owner: "10000000-0000-4000-8000-000000000001",
  admin: "10000000-0000-4000-8000-000000000002",
  tech: "10000000-0000-4000-8000-000000000003",
  design: "10000000-0000-4000-8000-000000000004",
  it: "20000000-0000-4000-8000-000000000001",
  marketing: "20000000-0000-4000-8000-000000000002",
  sales: "20000000-0000-4000-8000-000000000003",
  hotel: "30000000-0000-4000-8000-000000000001",
  teide: "30000000-0000-4000-8000-000000000002",
  events: "30000000-0000-4000-8000-000000000003",
  call: "40000000-0000-4000-8000-000000000001",
  work: "40000000-0000-4000-8000-000000000002",
};

const iso = () => new Date().toISOString();
const day = (offset = 0) => {
  const parts = new Intl.DateTimeFormat("en-GB", { timeZone: "Atlantic/Canary", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date());
  const value = (type: string) => parts.find((part) => part.type === type)?.value ?? "";
  const date = new Date(`${value("year")}-${value("month")}-${value("day")}T12:00:00Z`);
  date.setUTCDate(date.getUTCDate() + offset);
  return date.toISOString().slice(0, 10);
};
const dateTime = (offset = 0) => `${day(offset)}T10:00:00.000Z`;
const clone = <T,>(value: T): T => structuredClone(value);

type DemoRecurrence = { repeat_unit?: string; repeat_interval?: number; weekdays?: number[]; monthly_mode?: string; monthly_day?: number; monthly_week?: number; monthly_weekday?: number; ends_on?: string | null };

function nextOccurrence(start: string, rule: DemoRecurrence): string | null {
  const interval = Math.max(1, Math.floor(Number(rule.repeat_interval) || 1));
  const startDate = new Date(`${start}T12:00:00Z`);
  let candidate = new Date(startDate);
  if (rule.repeat_unit === "DAY") candidate.setUTCDate(candidate.getUTCDate() + interval);
  else if (rule.repeat_unit === "WEEK") {
    const weekdays = rule.weekdays?.length ? rule.weekdays : [(startDate.getUTCDay() + 6) % 7];
    for (let offset = 1; offset <= interval * 7 + 7; offset++) {
      candidate = new Date(startDate);
      candidate.setUTCDate(candidate.getUTCDate() + offset);
      const week = Math.floor((offset + (startDate.getUTCDay() + 6) % 7) / 7);
      if (week % interval === 0 && weekdays.includes((candidate.getUTCDay() + 6) % 7)) break;
    }
  } else if (rule.repeat_unit === "MONTH") {
    const targetMonth = startDate.getUTCMonth() + interval;
    const year = startDate.getUTCFullYear() + Math.floor(targetMonth / 12);
    const month = targetMonth % 12;
    const lastDay = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
    if (rule.monthly_mode === "NTH_WEEKDAY") {
      const weekday = Math.min(6, Math.max(0, Number(rule.monthly_weekday) || 0));
      const week = Math.min(5, Math.max(1, Number(rule.monthly_week) || 1));
      const matchingDays = Array.from({ length: lastDay }, (_, index) => index + 1)
        .filter((date) => (new Date(Date.UTC(year, month, date)).getUTCDay() + 6) % 7 === weekday);
      candidate = new Date(Date.UTC(year, month, week === 5 ? matchingDays.at(-1)! : matchingDays[Math.min(week - 1, matchingDays.length - 1)], 12));
    } else candidate = new Date(Date.UTC(year, month, Math.min(lastDay, Math.max(1, Number(rule.monthly_day) || startDate.getUTCDate())), 12));
  } else return null;
  const result = candidate.toISOString().slice(0, 10);
  return rule.ends_on && result > rule.ends_on ? null : result;
}

function initialState(): DemoState {
  const now = iso();
  const clients: DemoClient[] = [
    { id: ids.hotel, name: "Hotel Botánico", address: "Puerto de la Cruz, Tenerife", notes: "Seguimiento del formulario de reservas y mantenimiento preventivo.", created_at: now, updated_at: now, assigned_user_ids: [ids.tech, ids.admin], contacts: [
      { id: randomUUID(), full_name: "Elena Díaz", position: "Directora de operaciones", email: "elena.diaz@example.test", phone: "+34 922 000 101", notes: "Contacto principal para reservas.", created_at: now, updated_at: now },
      { id: randomUUID(), full_name: "Pablo Reyes", position: "Responsable de reservas", email: "pablo.reyes@example.test", phone: "+34 922 000 102", notes: null, created_at: now, updated_at: now },
    ] },
    { id: ids.teide, name: "Grupo Teide", address: "Las Palmas de Gran Canaria", notes: "Propuesta anual pendiente.", created_at: now, updated_at: now, assigned_user_ids: [ids.admin, ids.owner], contacts: [
      { id: randomUUID(), full_name: "Jorge Medina", position: "Director comercial", email: "jorge.medina@example.test", phone: "+34 928 000 404", notes: null, created_at: now, updated_at: now },
    ] },
    { id: ids.events, name: "Canarias Eventos", address: "Santa Cruz de Tenerife", notes: "Campaña de otoño.", created_at: now, updated_at: now, assigned_user_ids: [ids.design], contacts: [
      { id: randomUUID(), full_name: "Lucía Hernández", position: "Directora de proyectos", email: "lucia.hernandez@example.test", phone: "+34 922 000 303", notes: null, created_at: now, updated_at: now },
    ] },
  ];
  const users: DemoUser[] = [
    { id: ids.owner, full_name: "Marlon Farizo", email: "marlon@example.test", role: "OWNER", status: "ACTIVE", department_ids: [ids.it, ids.marketing, ids.sales] },
    { id: ids.admin, full_name: "Ana Torres", email: "ana@example.test", role: "ADMIN", status: "ACTIVE", department_ids: [ids.sales] },
    { id: ids.tech, full_name: "David Martín", email: "david@example.test", role: "EMPLOYEE", status: "ACTIVE", department_ids: [ids.it] },
    { id: ids.design, full_name: "Laura Suárez", email: "laura@example.test", role: "EMPLOYEE", status: "ACTIVE", department_ids: [ids.marketing] },
  ];
  const types = [{ id: ids.call, name: "Llamada", department_id: null }, { id: ids.work, name: "Trabajo", department_id: null }];
  const activity = (id: string, client_id: string, title: string, description: string, department_id: string, assigned_to_user_id: string, scheduled_for: string, status: Activity["status"]): Activity => ({
    id, client_id, user_id: ids.owner, user_name: "Marlon Farizo", assigned_to_user_id,
    assigned_to_name: users.find((user) => user.id === assigned_to_user_id)?.full_name ?? "",
    department_id, department_name: [{ id: ids.it, name: "Informática" }, { id: ids.marketing, name: "Marketing" }, { id: ids.sales, name: "Comercial" }].find((item) => item.id === department_id)?.name ?? null,
    activity_type_id: ids.work, activity_type_name: "Trabajo", title, description, next_action: null,
    scheduled_for, status, occurred_at: status === "COMPLETED" ? `${scheduled_for}T10:00:00.000Z` : null,
    completed_at: status === "COMPLETED" ? `${scheduled_for}T10:00:00.000Z` : null, schedule_id: null,
    created_at: now, updated_at: now, can_edit: true, can_delete: true,
  });
  const activities = [
    activity(randomUUID(), ids.hotel, "Confirmar estabilidad con el cliente", "Contactar tras una semana sin incidencias.", ids.it, ids.tech, day(), "PENDING"),
    activity(randomUUID(), ids.hotel, "Revisión del formulario de reservas", "Se corrigió la validación y se verificó el envío.", ids.it, ids.tech, day(), "COMPLETED"),
    activity(randomUUID(), ids.teide, "Enviar propuesta de renovación", "Preparar la propuesta anual de soporte.", ids.sales, ids.admin, day(3), "PENDING"),
    activity(randomUUID(), ids.events, "Planificación de campaña de otoño", "Se revisaron creatividades y calendario.", ids.marketing, ids.design, day(-1), "COMPLETED"),
    activity(randomUUID(), ids.teide, "Revisar propuesta comercial", "Confirmar condiciones antes de la reunión.", ids.sales, ids.owner, day(2), "PENDING"),
    activity(randomUUID(), ids.teide, "Preparar presupuesto inicial", "Se revisaron las partidas del servicio anual.", ids.sales, ids.owner, day(), "COMPLETED"),
  ];
  const audit: AuditEntry[] = [
    { id: randomUUID(), actor_user_id: ids.tech, actor_name: "David Martín", action: "COMPLETED_ACTIVITY", entity_type: "ACTIVITY", entity_id: activities[1].id, entity_name: activities[1].title, created_at: now, metadata: {}, metadata_names: {} },
    { id: randomUUID(), actor_user_id: ids.admin, actor_name: "Ana Torres", action: "ASSIGNED_CLIENT", entity_type: "CLIENT_ASSIGNMENT", entity_id: ids.teide, entity_name: "Grupo Teide", created_at: dateTime(-1), metadata: {}, metadata_names: {} },
    { id: randomUUID(), actor_user_id: ids.owner, actor_name: "Marlon Farizo", action: "CREATED_DEPARTMENT", entity_type: "DEPARTMENT", entity_id: ids.marketing, entity_name: "Marketing", created_at: dateTime(-2), metadata: {}, metadata_names: {} },
  ];
  return { clients, users, departments: [{ id: ids.it, name: "Informática" }, { id: ids.marketing, name: "Marketing" }, { id: ids.sales, name: "Comercial" }], activities, types, audit, summaries: [],
    aiConfiguration: { provider: "ollama", model: "Muestra preparada", has_api_key: false, source: "organization" } };
}

const demoGlobal = globalThis as typeof globalThis & {
  crmDemoSessions?: Map<string, { state: DemoState; updatedAt: number }>;
  crmDemoInitialState?: DemoState;
  crmDemoSchemaVersion?: number;
};
if (demoGlobal.crmDemoSchemaVersion !== 1) {
  demoGlobal.crmDemoSessions = new Map();
  demoGlobal.crmDemoInitialState = initialState();
  demoGlobal.crmDemoSchemaVersion = 1;
}
const sessions = demoGlobal.crmDemoSessions ??= new Map<string, { state: DemoState; updatedAt: number }>();
const seed = demoGlobal.crmDemoInitialState ??= initialState();
const maxAge = 24 * 60 * 60 * 1000;

export function demoState(sessionId?: string) {
  const session = sessionId ? sessions.get(sessionId) : undefined;
  if (session && Date.now() - session.updatedAt < maxAge) {
    session.updatedAt = Date.now();
    return session.state;
  }
  if (sessionId) sessions.delete(sessionId);
  return clone(seed);
}

function sessionForWrite(sessionId?: string) {
  for (const [key, session] of sessions) if (Date.now() - session.updatedAt >= maxAge) sessions.delete(key);
  if (sessions.size >= 500) sessions.delete(sessions.keys().next().value ?? "");
  if (sessionId && sessions.has(sessionId)) {
    const session = sessions.get(sessionId)!;
    session.updatedAt = Date.now();
    return { id: sessionId, state: session.state };
  }
  const id = randomUUID();
  const state = clone(seed);
  sessions.set(id, { state, updatedAt: Date.now() });
  return { id, state };
}

const asHistory = (activity: Activity, state: DemoState): HistoryEntry => ({
  ...activity, client_name: state.clients.find((client) => client.id === activity.client_id)?.name ?? "Cliente",
  person_id: activity.assigned_to_user_id, person_name: activity.assigned_to_name,
});
const parsePath = (path: string) => new URL(path, "http://demo.local");
const page = <T,>(items: T[], url: URL) => {
  const offset = Math.max(0, Number(url.searchParams.get("offset") ?? 0) || 0);
  const limit = Math.min(100, Math.max(1, Number(url.searchParams.get("limit") ?? 20) || 20));
  return { items: items.slice(offset, offset + limit), has_more: items.length > offset + limit };
};
const json = (value: unknown, status = 200) => Response.json(value, { status });
const error = (status: number, detail: string) => json({ detail }, status);

export function demoRead(path: string, sessionId?: string): Response {
  const state = demoState(sessionId);
  const url = parsePath(path);
  const segments = url.pathname.split("/").filter(Boolean);
  const allActivities = [...state.activities].sort((a, b) => Number(b.status === "PENDING") - Number(a.status === "PENDING") || a.scheduled_for.localeCompare(b.scheduled_for));
  if (url.pathname === "/workspace" || url.pathname === "/auth/me") return json({ user_id: ids.owner, organization_name: "Organización Ejemplo", organization_mode: "BUSINESS", user_name: "Marlon Farizo", user_email: "marlon@example.test", user_role: "OWNER", departments: state.departments } satisfies Workspace);
  if (url.pathname === "/admin/departments") return json(state.departments);
  if (url.pathname === "/admin/users") return json(state.users);
  if (url.pathname === "/activity-types") return json(state.types);
  if (url.pathname === "/clients") {
    const search = (url.searchParams.get("search") ?? "").toLocaleLowerCase("es");
    return json(state.clients.filter((client) => client.name.toLocaleLowerCase("es").includes(search)).map(({ id, name, address, created_at, updated_at }) => ({ id, name, address, created_at, updated_at } satisfies ClientSummary)));
  }
  if (segments[0] === "clients" && segments[1]) {
    const client = state.clients.find((item) => item.id === segments[1]);
    if (!client) return error(404, "Client not found");
    if (segments.length === 2) return json(client);
    if (segments[2] === "assignments") {
      const assigned = state.users.filter((user) => client.assigned_user_ids.includes(user.id)).map((user) => ({ user_id: user.id, full_name: user.full_name, status: user.status }));
      const available = state.users.filter((user) => user.status === "ACTIVE" && !client.assigned_user_ids.includes(user.id)).map((user) => ({ user_id: user.id, full_name: user.full_name, status: user.status }));
      return json({ assigned, available } satisfies AssignmentTeam);
    }
    if (segments[2] === "history") return json({ ...page(state.activities.filter((item) => item.client_id === client.id).map((item) => asHistory(item, state)), url) } satisfies HistoryPage);
    if (segments[2] === "activities") {
      const period = url.searchParams.get("period") ?? "TODAY";
      const filtered = state.activities.filter((item) => item.client_id === client.id
        && (!url.searchParams.get("activity_type_id") || item.activity_type_id === url.searchParams.get("activity_type_id"))
        && (!url.searchParams.get("department_id") || item.department_id === url.searchParams.get("department_id"))
        && (period === "HISTORY" ? item.scheduled_for < day() : period === "SCHEDULED" ? item.scheduled_for > day() : item.scheduled_for === day()));
      return json({ ...page(filtered, url), departments: state.departments,
        candidates: state.users.filter((user) => user.status === "ACTIVE").map((user) => ({ id: user.id, name: user.full_name, department_ids: user.department_ids })),
        activity_types: state.types, can_create: true, can_manage_types: true } satisfies ActivityPage);
    }
    if (segments[2] === "tasks") return json(taskPage(state, allActivities.filter((item) => item.client_id === client.id), url, true));
  }
  if (url.pathname === "/tasks/mine") return json(taskPage(state, allActivities.filter((item) => item.assigned_to_user_id === ids.owner), url, false));
  if (url.pathname === "/dashboard") {
    const today = state.activities.filter((item) => item.scheduled_for === day() || item.completed_at?.slice(0, 10) === day());
    const todayCompleted = today.filter((item) => item.completed_at?.slice(0, 10) === day());
    const data: Dashboard = {
      metrics: { clients: state.clients.length, pending_tasks: state.activities.filter((item) => item.status === "PENDING").length,
        completed_tasks: todayCompleted.length, activities: state.activities.length,
        today_clients: new Set(today.map((item) => item.client_id)).size, today_activities: today.length,
        today_pending_tasks: today.filter((item) => item.status === "PENDING").length,
        active_users: state.users.filter((user) => user.status === "ACTIVE").length, departments: state.departments.length },
      departments: state.departments.map((department) => ({ ...department,
        active_employees: state.users.filter((user) => user.status === "ACTIVE" && user.department_ids.includes(department.id)).length,
        activities: today.filter((item) => item.department_id === department.id).length,
        pending_tasks: state.activities.filter((item) => item.department_id === department.id && item.status === "PENDING").length })),
      today_activities: today.map((item) => asHistory(item, state)), recent_activities: state.activities.map((item) => asHistory(item, state)),
      pending_tasks: state.activities.filter((item) => item.status === "PENDING").map((item) => asHistory(item, state)),
    };
    return json(data);
  }
  if (url.pathname === "/audit") {
    const categoryActions: Record<string, string[]> = { CLIENTS: ["CREATED_CLIENT", "UPDATED_CLIENT", "CREATED_CLIENT_CONTACT", "UPDATED_CLIENT_CONTACT", "DELETED_CLIENT_CONTACT", "ASSIGNED_CLIENT", "UNASSIGNED_CLIENT"], TEAM: ["CREATED_DEPARTMENT", "UPDATED_DEPARTMENT", "DELETED_DEPARTMENT", "CREATED_USER", "UPDATED_USER"], ACTIVITY: ["CREATED_ACTIVITY", "UPDATED_ACTIVITY", "COMPLETED_ACTIVITY", "DELETED_ACTIVITY"], AI: ["AI_SUMMARY_COMPLETED"] };
    const items = state.audit.filter((entry) => (!url.searchParams.get("category") || (categoryActions[url.searchParams.get("category")!] ?? []).includes(entry.action))
      && (!url.searchParams.get("action") || entry.action === url.searchParams.get("action"))
      && (!url.searchParams.get("actor_user_id") || entry.actor_user_id === url.searchParams.get("actor_user_id"))
      && (!url.searchParams.get("since") || entry.created_at >= url.searchParams.get("since")!)
      && (!url.searchParams.get("until") || entry.created_at <= url.searchParams.get("until")!));
    return json({ ...page(items, url), actors: state.users.map((user) => ({ id: user.id, name: user.full_name })) } satisfies AuditPage);
  }
  if (url.pathname === "/ai/options") return json({ enabled: state.aiConfiguration.provider !== "disabled", provider: state.aiConfiguration.provider,
    model: state.aiConfiguration.model, external: false, departments: state.departments } satisfies SummaryOptions);
  if (url.pathname === "/ai/configuration") return json(state.aiConfiguration);
  if (url.pathname === "/ai/summaries/latest") return json(state.summaries.filter((item) =>
    (!url.searchParams.get("department_id") || item.section.department_id === url.searchParams.get("department_id"))
    && (!url.searchParams.get("client_id") || item.section.sources.some((source) => source.client_id === url.searchParams.get("client_id")))));
  return error(404, "Demo endpoint not found");
}

function taskPage(state: DemoState, activities: Activity[], url: URL, client: boolean): TaskPage {
  const filtered = activities.filter((item) => !url.searchParams.get("status") || item.status === url.searchParams.get("status"));
  return { ...page(filtered.map((item): Task => ({
    id: item.id, client_id: item.client_id, client_name: state.clients.find((entry) => entry.id === item.client_id)?.name ?? "Cliente",
    title: item.title ?? item.description, description: item.description, assigned_to_user_id: item.assigned_to_user_id,
    assigned_to_name: item.assigned_to_name, created_by_user_id: item.user_id,
    department_id: item.department_id, department_name: item.department_name, due_at: `${item.scheduled_for}T10:00:00Z`,
    status: item.status, completed_at: item.completed_at, created_at: item.created_at, updated_at: item.updated_at,
  })), url), options: client ? { individual: false, departments: state.departments,
    candidates: state.users.filter((user) => user.status === "ACTIVE").map((user) => ({ id: user.id, name: user.full_name, department_ids: user.department_ids })) } : null };
}

function record(state: DemoState, action: string, entity_type: string, entity_id: string, entity_name: string) {
  state.audit.unshift({ id: randomUUID(), actor_user_id: ids.owner, actor_name: "Marlon Farizo", action,
    entity_type, entity_id, entity_name, created_at: iso(), metadata: {}, metadata_names: {} });
}

export async function demoWrite(path: string, method: string, payload: unknown, sessionId?: string): Promise<{ response: Response; sessionId: string }> {
  const session = sessionForWrite(sessionId);
  const state = session.state;
  const url = parsePath(path);
  const segments = url.pathname.split("/").filter(Boolean);
  const body = typeof payload === "object" && payload !== null ? payload as Record<string, unknown> : {};
  const value = (key: string) => String(body[key] ?? "").trim();
  const done = (response: Response) => ({ response, sessionId: session.id });
  const findClient = () => state.clients.find((item) => item.id === segments[1]);
  if (url.pathname === "/clients" && method === "POST") {
    if (!value("name")) return done(error(422, "Name required"));
    const client: DemoClient = { id: randomUUID(), name: value("name"), address: value("address") || null,
      notes: value("notes") || null, contacts: [], assigned_user_ids: [], created_at: iso(), updated_at: iso() };
    state.clients.push(client); record(state, "CREATED_CLIENT", "CLIENT", client.id, client.name);
    return done(json(client, 201));
  }
  if (segments[0] === "clients" && segments[1]) {
    const client = findClient();
    if (!client) return done(error(404, "Client not found"));
    if (segments.length === 2 && method === "PATCH") {
      if (!value("name")) return done(error(422, "Name required"));
      client.name = value("name"); client.address = value("address") || null; client.notes = value("notes") || null; client.updated_at = iso();
      record(state, "UPDATED_CLIENT", "CLIENT", client.id, client.name); return done(json(client));
    }
    if (segments[2] === "contacts") {
      if (segments.length === 3 && method === "POST") {
        if (!value("full_name")) return done(error(422, "Name required"));
        const contact: ClientContact = { id: randomUUID(), full_name: value("full_name"), position: value("position") || null,
          email: value("email") || null, phone: value("phone") || null, notes: value("notes") || null, created_at: iso(), updated_at: iso() };
        client.contacts.push(contact); record(state, "CREATED_CLIENT_CONTACT", "CLIENT_CONTACT", contact.id, contact.full_name);
        return done(json(contact, 201));
      }
      const contact = client.contacts.find((item) => item.id === segments[3]);
      if (!contact) return done(error(404, "Contact not found"));
      if (method === "DELETE") {
        client.contacts = client.contacts.filter((item) => item.id !== contact.id);
        record(state, "DELETED_CLIENT_CONTACT", "CLIENT_CONTACT", contact.id, contact.full_name);
        return done(new Response(null, { status: 204 }));
      }
      if (method === "PATCH") {
        if (!value("full_name")) return done(error(422, "Name required"));
        contact.full_name = value("full_name"); contact.position = value("position") || null; contact.email = value("email") || null;
        contact.phone = value("phone") || null; contact.notes = value("notes") || null; contact.updated_at = iso();
        record(state, "UPDATED_CLIENT_CONTACT", "CLIENT_CONTACT", contact.id, contact.full_name); return done(json(contact));
      }
    }
    if (segments[2] === "assignments") {
      if (method === "POST") {
        const id = value("user_id"); if (!state.users.some((item) => item.id === id)) return done(error(404, "User not found"));
        if (client.assigned_user_ids.includes(id)) return done(error(409, "Already assigned"));
        client.assigned_user_ids.push(id); record(state, "ASSIGNED_CLIENT", "CLIENT_ASSIGNMENT", client.id, client.name);
        return done(new Response(null, { status: 204 }));
      }
      if (method === "DELETE") {
        client.assigned_user_ids = client.assigned_user_ids.filter((id) => id !== segments[3]);
        record(state, "UNASSIGNED_CLIENT", "CLIENT_ASSIGNMENT", client.id, client.name);
        return done(new Response(null, { status: 204 }));
      }
    }
    if (segments[2] === "activities" || segments[2] === "tasks") {
      const task = segments[2] === "tasks";
      const activity = state.activities.find((item) => item.id === segments[3] && item.client_id === client.id);
      if (segments.length === 3 && method === "POST") {
        const departmentId = value("department_id") || state.departments[0]?.id;
        const assigneeId = value("assigned_to_user_id") || ids.owner;
        const department = state.departments.find((item) => item.id === departmentId);
        const assignee = state.users.find((item) => item.id === assigneeId);
        if (!department || !assignee) return done(error(409, "Invalid assignment"));
        const status = value("status") === "COMPLETED" ? "COMPLETED" : "PENDING";
        const created: Activity = { id: randomUUID(), client_id: client.id, user_id: ids.owner, user_name: "Marlon Farizo",
          assigned_to_user_id: assignee.id, assigned_to_name: assignee.full_name, department_id: department.id,
          department_name: department.name, activity_type_id: value("activity_type_id") || ids.work,
          activity_type_name: state.types.find((item) => item.id === value("activity_type_id"))?.name ?? "Trabajo",
          title: value("title") || null, description: value("description") || value("title"), next_action: value("next_action") || null,
          scheduled_for: (value("scheduled_for") || value("due_at").slice(0, 10) || day()), status,
          occurred_at: status === "COMPLETED" ? iso() : null, completed_at: status === "COMPLETED" ? iso() : null,
          schedule_id: null, created_at: iso(), updated_at: iso(), can_edit: true, can_delete: true };
        const recurrence = body.recurrence && typeof body.recurrence === "object" ? body.recurrence as DemoRecurrence : null;
        const followingDate = recurrence && status === "PENDING" ? nextOccurrence(created.scheduled_for, recurrence) : null;
        const following = followingDate ? { ...created, id: randomUUID(), scheduled_for: followingDate } : null;
        if (following) {
          created.schedule_id = randomUUID();
          following.schedule_id = created.schedule_id;
        }
        state.activities.unshift(created, ...(following ? [following] : []));
        record(state, "CREATED_ACTIVITY", "ACTIVITY", created.id, created.title ?? created.description);
        return done(json(following ? [created, following] : [created], 201));
      }
      if (!activity) return done(error(404, "Activity not found"));
      if (segments[4] === "complete" && method === "POST") {
        activity.status = "COMPLETED"; activity.completed_at = iso(); activity.occurred_at = iso(); activity.updated_at = iso();
        record(state, "COMPLETED_ACTIVITY", "ACTIVITY", activity.id, activity.title ?? activity.description);
        return done(new Response(null, { status: 204 }));
      }
      if (method === "PATCH") {
        activity.title = value("title") || activity.title; activity.description = value("description") || activity.description;
        activity.next_action = value("next_action") || null;
        activity.scheduled_for = value("scheduled_for") || value("due_at").slice(0, 10) || activity.scheduled_for;
        activity.activity_type_id = value("activity_type_id") || activity.activity_type_id;
        activity.activity_type_name = state.types.find((item) => item.id === activity.activity_type_id)?.name ?? activity.activity_type_name;
        activity.assigned_to_user_id = value("assigned_to_user_id") || activity.assigned_to_user_id;
        activity.assigned_to_name = state.users.find((item) => item.id === activity.assigned_to_user_id)?.full_name ?? activity.assigned_to_name;
        activity.occurred_at = value("occurred_at") || activity.occurred_at; activity.updated_at = iso();
        record(state, "UPDATED_ACTIVITY", "ACTIVITY", activity.id, activity.title ?? activity.description);
        return done(new Response(null, { status: 204 }));
      }
      if (method === "DELETE") {
        const deleteFollowing = url.searchParams.get("scope") === "THIS_AND_FOLLOWING" && activity.schedule_id;
        state.activities = state.activities.filter((item) => item.id !== activity.id
          && !(deleteFollowing && item.schedule_id === activity.schedule_id && item.scheduled_for >= activity.scheduled_for));
        record(state, "DELETED_ACTIVITY", "ACTIVITY", activity.id, activity.title ?? activity.description);
        return done(new Response(null, { status: 204 }));
      }
      if (task) return done(error(405, "Method not allowed"));
    }
  }
  if (segments[0] === "admin" && segments[1] === "departments") {
    if (segments.length === 2 && method === "POST") {
      if (!value("name") || state.departments.some((item) => item.name.toLowerCase() === value("name").toLowerCase())) return done(error(409, "Duplicate department"));
      const department = { id: randomUUID(), name: value("name") }; state.departments.push(department);
      record(state, "CREATED_DEPARTMENT", "DEPARTMENT", department.id, department.name); return done(json(department, 201));
    }
    const department = state.departments.find((item) => item.id === segments[2]);
    if (!department) return done(error(404, "Department not found"));
    if (method === "PATCH") {
      department.name = value("name"); state.activities.filter((item) => item.department_id === department.id).forEach((item) => { item.department_name = department.name; });
      record(state, "UPDATED_DEPARTMENT", "DEPARTMENT", department.id, department.name); return done(json(department));
    }
    if (method === "DELETE") {
      if (state.activities.some((item) => item.department_id === department.id)) return done(error(409, "Department has activity"));
      state.departments = state.departments.filter((item) => item.id !== department.id);
      state.users.forEach((user) => { user.department_ids = user.department_ids.filter((id) => id !== department.id); });
      record(state, "DELETED_DEPARTMENT", "DEPARTMENT", department.id, department.name); return done(new Response(null, { status: 204 }));
    }
  }
  if (segments[0] === "admin" && segments[1] === "users") {
    if (segments.length === 2 && method === "POST") {
      const user: DemoUser = { id: randomUUID(), email: value("email"), full_name: value("full_name"),
        role: value("role") === "ADMIN" ? "ADMIN" : "EMPLOYEE", status: "PENDING",
        department_ids: Array.isArray(body.department_ids) ? body.department_ids.map(String) : [] };
      state.users.push(user); record(state, "CREATED_USER", "USER", user.id, user.full_name); return done(json(user, 201));
    }
    const user = state.users.find((item) => item.id === segments[2]);
    if (!user) return done(error(404, "User not found"));
    if (method === "PATCH") {
      user.full_name = value("full_name") || user.full_name; user.role = value("role") === "ADMIN" ? "ADMIN" : "EMPLOYEE";
      user.department_ids = Array.isArray(body.department_ids) ? body.department_ids.map(String) : [];
      record(state, "UPDATED_USER", "USER", user.id, user.full_name); return done(json(user));
    }
    if (method === "POST" && segments[3] === "disable") user.status = "DISABLED";
    else if (method === "POST" && segments[3] === "activate") user.status = "ACTIVE";
    else if (method !== "POST" || segments[3] !== "invitation") return done(error(404, "Unknown action"));
    return done(new Response(null, { status: 204 }));
  }
  if (url.pathname === "/activity-types" && method === "POST") {
    const type = { id: randomUUID(), name: value("name"), department_id: value("department_id") || null };
    state.types.push(type); return done(json(type, 201));
  }
  if (url.pathname === "/ai/configuration" && method === "PUT") {
    if (value("provider") !== "disabled" && value("provider") !== "ollama") return done(error(422, "External providers are unavailable in demo mode"));
    state.aiConfiguration = { provider: value("provider") === "disabled" ? "disabled" : "ollama",
      model: value("provider") === "disabled" ? "" : value("model") || "Muestra preparada",
      has_api_key: false, source: "organization" };
    record(state, "UPDATED_AI_CONFIGURATION", "AI_CONFIGURATION", ids.owner, "Opciones de IA");
    return done(json(state.aiConfiguration));
  }
  if (url.pathname === "/ai/summaries" && method === "POST") {
    if (state.aiConfiguration.provider === "disabled") return done(error(409, "AI_NOT_CONFIGURED"));
    const scope = value("scope");
    const selected = state.activities.filter((item) =>
      (scope === "CLIENT" ? item.client_id === value("client_id") : scope === "DEPARTMENT" ? item.department_id === value("department_id") : true)
      && item.scheduled_for >= value("since").slice(0, 10) && item.scheduled_for <= value("until").slice(0, 10));
    const groups = new Map<string, Activity[]>();
    for (const item of selected) groups.set(item.department_id ?? "", [...(groups.get(item.department_id ?? "") ?? []), item]);
    const sections: SummaryResult["sections"] = [...groups.entries()].map(([departmentId, activities]) => {
      const sources = activities.map((item) => ({ id: item.id, client_id: item.client_id,
        client_name: state.clients.find((client) => client.id === item.client_id)?.name ?? "Cliente",
        activity_type_name: item.activity_type_name, title: item.title, description: item.description,
        status: item.status, scheduled_for: item.scheduled_for, occurred_at: item.occurred_at }));
      const completed = activities.filter((item) => item.status === "COMPLETED").length;
      return { department_id: departmentId || null,
        department_name: state.departments.find((item) => item.id === departmentId)?.name ?? null,
        content: { summary: `Se registraron ${activities.length} ${activities.length === 1 ? "actividad" : "actividades"} en el periodo; ${completed} ${completed === 1 ? "completada" : "completadas"}.`,
          pending_actions: activities.filter((item) => item.status === "PENDING").map((item) => item.next_action || item.title || item.description),
          source_ids: sources.map((item) => item.id) }, sources };
    });
    const result: SummaryResult = { request_id: randomUUID(), generated_at: iso(), provider: "Demo", model: state.aiConfiguration.model, cached: false,
      usage: null, sections };
    state.summaries.unshift(...sections.map((section) => ({ generated_at: result.generated_at, since: value("since"), until: value("until"),
      provider: result.provider, model: result.model, section })));
    record(state, "AI_SUMMARY_COMPLETED", "AI_SUMMARY", result.request_id!, "Resumen de actividad");
    return done(json(result));
  }
  if (url.pathname === "/auth/logout" && method === "POST") return done(new Response(null, { status: 204 }));
  return done(error(404, "Demo endpoint not found"));
}
