export const auditActions: Record<string, string> = {
  UPDATED_AI_CONFIGURATION: "Configuración de IA actualizada",
  AI_SUMMARY_REQUESTED: "Resumen IA solicitado", AI_SUMMARY_COMPLETED: "Resumen IA completado", AI_SUMMARY_FAILED: "Resumen IA fallido",
  INITIALIZED_ORGANIZATION: "Instalación inicializada", UPDATED_ORGANIZATION: "Organización actualizada",
  AUTH_LOGIN: "Inicio de sesión", AUTH_LOGOUT: "Cierre de sesión", PASSWORD_CHANGED: "Contraseña cambiada",
  CREATED_USER: "Usuario creado", UPDATED_USER: "Datos y permisos del usuario actualizados", DISABLED_USER: "Usuario desactivado",
  ACTIVATED_USER: "Usuario activado", ACCEPTED_INVITATION: "Invitación aceptada", RESENT_INVITATION: "Invitación reenviada",
  CREATED_DEPARTMENT: "Departamento creado", UPDATED_DEPARTMENT: "Departamento actualizado", DELETED_DEPARTMENT: "Departamento eliminado",
  CREATED_CLIENT: "Cliente creado", UPDATED_CLIENT: "Cliente actualizado",
  CREATED_CLIENT_CONTACT: "Contacto creado", UPDATED_CLIENT_CONTACT: "Contacto actualizado", DELETED_CLIENT_CONTACT: "Contacto eliminado",
  ASSIGNED_CLIENT: "Cliente asignado", UNASSIGNED_CLIENT: "Asignación retirada",
  CREATED_ACTIVITY: "Actividad registrada", UPDATED_ACTIVITY: "Actividad actualizada",
  COMPLETED_ACTIVITY: "Actividad completada", DELETED_ACTIVITY: "Actividad eliminada",
  CREATED_TASK: "Tarea creada", UPDATED_TASK: "Tarea actualizada", COMPLETED_TASK: "Tarea completada", REASSIGNED_TASK: "Tarea reasignada",
};
export type AuditCategory = "" | "ACCESS" | "TEAM" | "CLIENTS" | "ACTIVITY" | "ORGANIZATION" | "AI";
export const auditCategories: { value: AuditCategory; label: string }[] = [
  { value: "", label: "Todo" },
  { value: "ACCESS", label: "Accesos" },
  { value: "TEAM", label: "Equipo y permisos" },
  { value: "CLIENTS", label: "Clientes" },
  { value: "ACTIVITY", label: "Actividad" },
  { value: "ORGANIZATION", label: "Organización" },
  { value: "AI", label: "IA" },
];
export const auditCategoryDescriptions: Record<AuditCategory, string> = {
  "": "Todas las acciones registradas, ordenadas desde la más reciente.",
  ACCESS: "Inicios y cierres de sesión explícitos. Cerrar el navegador o dejar caducar la sesión no registra una salida.",
  TEAM: "Cambios en usuarios, perfiles, permisos, invitaciones y departamentos.",
  CLIENTS: "Altas y cambios de clientes, contactos y responsables asignados.",
  ACTIVITY: "Actividades registradas, actualizadas, completadas o eliminadas.",
  ORGANIZATION: "Configuración general y puesta en marcha de la organización.",
  AI: "Solicitudes de resumen y resultado del servicio de inteligencia artificial.",
};
export const auditCategoryActions: Record<Exclude<AuditCategory, "">, string[]> = {
  ACCESS: ["AUTH_LOGIN", "AUTH_LOGOUT"],
  TEAM: [
    "PASSWORD_CHANGED", "CREATED_USER", "UPDATED_USER", "DISABLED_USER", "ACTIVATED_USER",
    "ACCEPTED_INVITATION", "RESENT_INVITATION", "CREATED_DEPARTMENT", "UPDATED_DEPARTMENT",
    "DELETED_DEPARTMENT",
  ],
  CLIENTS: [
    "CREATED_CLIENT", "UPDATED_CLIENT", "CREATED_CLIENT_CONTACT", "UPDATED_CLIENT_CONTACT",
    "DELETED_CLIENT_CONTACT", "ASSIGNED_CLIENT", "UNASSIGNED_CLIENT",
  ],
  ACTIVITY: [
    "CREATED_ACTIVITY", "UPDATED_ACTIVITY", "COMPLETED_ACTIVITY", "DELETED_ACTIVITY",
    "CREATED_TASK", "UPDATED_TASK", "COMPLETED_TASK", "REASSIGNED_TASK",
  ],
  ORGANIZATION: ["INITIALIZED_ORGANIZATION", "UPDATED_ORGANIZATION"],
  AI: ["AI_SUMMARY_REQUESTED", "AI_SUMMARY_COMPLETED", "AI_SUMMARY_FAILED", "UPDATED_AI_CONFIGURATION"],
};
export const entityLabels: Record<string, string> = {
  AI_CONFIGURATION: "Configuración de IA",
  AI_SUMMARY: "Solicitud de resumen IA",
  ORGANIZATION: "Organización", USER: "Usuario", USER_SESSION: "Sesión", DEPARTMENT: "Departamento",
  CLIENT: "Cliente", CLIENT_CONTACT: "Contacto", CLIENT_ASSIGNMENT: "Asignación", ACTIVITY: "Actividad", TASK: "Tarea",
};
export const metadataLabels: Record<string, string> = {
  scope: "Alcance", provider: "Servicio de IA", model: "Modelo", source_ids: "Actividades incluidas", context_sha256: "Verificación del contexto", error_code: "Resultado",
  name: "Nombre", previous_name: "Nombre anterior", full_name: "Nombre completo", previous: "Datos anteriores",
  role: "Perfil", client_id: "Cliente", user_id: "Usuario", department_id: "Departamento",
  assigned_to_user_id: "Responsable", previous_assigned_to_user_id: "Responsable anterior",
  department_ids: "Departamentos asignados", previous_department_ids: "Departamentos anteriores", changed_fields: "Información modificada",
};
const roleLabels: Record<string, string> = { OWNER: "Propietario", ADMIN: "Administrador", EMPLOYEE: "Empleado" };
const scopeLabels: Record<string, string> = {
  CLIENT: "Cliente", DEPARTMENT: "Departamento", ORGANIZATION: "Organización",
  THIS: "Solo esta actividad", THIS_AND_FOLLOWING: "Esta actividad y las siguientes",
};
const errorLabels: Record<string, string> = {
  AI_PROVIDER_UNAVAILABLE: "El servicio de IA no estaba disponible",
  AI_INVALID_OUTPUT: "La respuesta de IA no tenía un formato válido",
  AI_ACCESS_CHANGED: "Los permisos cambiaron durante la solicitud",
  AI_TIMEOUT: "El servicio de IA tardó demasiado en responder",
};
const providerLabels: Record<string, string> = {
  disabled: "Desactivada", ollama: "Ollama local", openai: "OpenAI",
  anthropic: "Anthropic Claude", gemini: "Google Gemini",
};
const changedFieldLabels: Record<string, string> = {
  name: "nombre", address: "dirección", notes: "notas", full_name: "nombre completo",
  position: "cargo", email: "correo electrónico", phone: "teléfono", role: "perfil",
  department_ids: "departamentos", type: "tipo de actividad", description: "descripción",
  next_action: "próxima acción", occurred_at: "fecha de realización", title: "título",
  assigned_to_user_id: "responsable", due_at: "fecha prevista", scheduled_for: "fecha programada",
  activity_type_id: "tipo de actividad", status: "estado", completed_at: "fecha de finalización",
};
export type AuditEntry = {
  id: string; actor_user_id: string | null; actor_name: string | null; action: string;
  entity_type: string; entity_id: string; entity_name: string | null; created_at: string;
  metadata: Record<string, unknown>; metadata_names: Record<string, string | string[]>;
};
export type AuditActor = { id: string; name: string };
export type AuditPage = { items: AuditEntry[]; actors: AuditActor[]; has_more: boolean };
export type AuditFilters = {
  category: AuditCategory; action: string; actor_user_id: string; entity_id: string;
  since: string; until: string; offset: number;
};
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const dateTime = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/;

export function parseAuditFilters(query: Record<string, string | string[] | undefined>): AuditFilters {
  const value = (key: string) => typeof query[key] === "string" ? query[key] as string : "";
  const date = (key: string) => {
    const parsed = new Date(`${value(key)}:00Z`);
    return dateTime.test(value(key)) && Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 16) === value(key) ? value(key) : "";
  };
  const offset = Number(value("offset"));
  const category = auditCategories.some((item) => item.value === value("category"))
    ? value("category") as AuditCategory : "";
  const rawAction = Object.hasOwn(auditActions, value("action")) ? value("action") : "";
  const action = category && rawAction && !auditCategoryActions[category].includes(rawAction)
    ? "" : rawAction;
  return { category, action,
    actor_user_id: uuid.test(value("actor_user_id")) ? value("actor_user_id") : "",
    entity_id: uuid.test(value("entity_id")) ? value("entity_id") : "", since: date("since"), until: date("until"),
    offset: Number.isInteger(offset) && offset >= 0 && offset <= 100000 ? offset : 0 };
}

export function auditQuery(filters: AuditFilters, api = false) {
  const query = new URLSearchParams({ offset: String(filters.offset) });
  if (filters.category) query.set("category", filters.category);
  for (const key of ["action", "actor_user_id", "entity_id", "since", "until"] as const) {
    if (filters[key]) query.set(key, api && ["since", "until"].includes(key) ? `${filters[key]}:00Z` : filters[key]);
  }
  return query.toString();
}

export function auditActionsForCategory(category: AuditCategory) {
  const allowed = category ? new Set(auditCategoryActions[category]) : null;
  return Object.entries(auditActions).filter(([action]) => !allowed || allowed.has(action));
}

export function auditMetadataValue(entry: AuditEntry, key: string, value: unknown): string {
  const resolved = entry.metadata_names[key];
  if (resolved) return Array.isArray(resolved) ? resolved.join(", ") : resolved;
  if (value === null) return "Sin valor";
  if (key === "changed_fields" && Array.isArray(value)) {
    return value.map((field) => changedFieldLabels[String(field)] ?? "otro dato").join(", ");
  }
  if (key === "source_ids" && Array.isArray(value)) {
    return `${value.length} ${value.length === 1 ? "actividad" : "actividades"}`;
  }
  if (key === "context_sha256") return "Comprobada";
  if (key === "role" && typeof value === "string") return roleLabels[value] ?? value;
  if (key === "scope" && typeof value === "string") return scopeLabels[value] ?? value;
  if (key === "error_code" && typeof value === "string") return errorLabels[value] ?? "Error del servicio";
  if (key === "provider" && typeof value === "string") return providerLabels[value] ?? value;
  if (key === "previous" && typeof value === "object" && value) {
    const previous = value as { full_name?: string; role?: string };
    return [previous.full_name, previous.role ? roleLabels[previous.role] ?? previous.role : null]
      .filter(Boolean).join(" · ");
  }
  if (key.endsWith("_id") || key.endsWith("_ids")) return "Referencia no disponible";
  if (Array.isArray(value)) return value.map(String).join(", ");
  if (typeof value === "string") return value;
  return "Información disponible";
}
