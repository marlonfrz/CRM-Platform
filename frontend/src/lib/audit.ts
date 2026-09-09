export const auditActions: Record<string, string> = {
  INITIALIZED_ORGANIZATION: "Instalación inicializada", UPDATED_ORGANIZATION: "Organización actualizada",
  AUTH_LOGIN: "Inicio de sesión", AUTH_LOGOUT: "Cierre de sesión", PASSWORD_CHANGED: "Contraseña cambiada",
  CREATED_USER: "Usuario creado", UPDATED_USER: "Usuario actualizado", DISABLED_USER: "Usuario desactivado",
  ACTIVATED_USER: "Usuario activado", ACCEPTED_INVITATION: "Invitación aceptada", RESENT_INVITATION: "Invitación reenviada",
  CREATED_DEPARTMENT: "Departamento creado", UPDATED_DEPARTMENT: "Departamento actualizado", DELETED_DEPARTMENT: "Departamento eliminado",
  CREATED_CLIENT: "Cliente creado", UPDATED_CLIENT: "Cliente actualizado",
  CREATED_CLIENT_CONTACT: "Contacto creado", UPDATED_CLIENT_CONTACT: "Contacto actualizado", DELETED_CLIENT_CONTACT: "Contacto eliminado",
  ASSIGNED_CLIENT: "Cliente asignado", UNASSIGNED_CLIENT: "Asignación retirada",
  CREATED_ACTIVITY: "Actividad registrada", UPDATED_ACTIVITY: "Actividad corregida",
  CREATED_TASK: "Tarea creada", UPDATED_TASK: "Tarea actualizada", COMPLETED_TASK: "Tarea completada", REASSIGNED_TASK: "Tarea reasignada",
};
export const entityLabels: Record<string, string> = {
  ORGANIZATION: "Organización", USER: "Usuario", USER_SESSION: "Sesión", DEPARTMENT: "Departamento",
  CLIENT: "Cliente", CLIENT_CONTACT: "Contacto", CLIENT_ASSIGNMENT: "Asignación", ACTIVITY: "Actividad", TASK: "Tarea",
};
export const metadataLabels: Record<string, string> = {
  name: "Nombre", previous_name: "Nombre anterior", full_name: "Nombre completo", previous: "Datos anteriores",
  role: "Rol", client_id: "ID del cliente", user_id: "ID del usuario", department_id: "ID del departamento",
  assigned_to_user_id: "ID del responsable", previous_assigned_to_user_id: "ID del responsable anterior",
  department_ids: "Departamentos asignados (IDs)", previous_department_ids: "Departamentos anteriores (IDs)", changed_fields: "Campos modificados",
};
export type AuditEntry = {
  id: string; actor_user_id: string | null; actor_name: string | null; action: string;
  entity_type: string; entity_id: string; created_at: string; metadata: Record<string, unknown>;
};
export type AuditPage = { items: AuditEntry[]; has_more: boolean };
export type AuditFilters = { action: string; actor_user_id: string; entity_id: string; since: string; until: string; offset: number };
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const dateTime = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/;

export function parseAuditFilters(query: Record<string, string | string[] | undefined>): AuditFilters {
  const value = (key: string) => typeof query[key] === "string" ? query[key] as string : "";
  const date = (key: string) => {
    const parsed = new Date(`${value(key)}:00Z`);
    return dateTime.test(value(key)) && Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 16) === value(key) ? value(key) : "";
  };
  const offset = Number(value("offset"));
  return { action: Object.hasOwn(auditActions, value("action")) ? value("action") : "",
    actor_user_id: uuid.test(value("actor_user_id")) ? value("actor_user_id") : "",
    entity_id: uuid.test(value("entity_id")) ? value("entity_id") : "", since: date("since"), until: date("until"),
    offset: Number.isInteger(offset) && offset >= 0 && offset <= 100000 ? offset : 0 };
}

export function auditQuery(filters: AuditFilters, api = false) {
  const query = new URLSearchParams({ offset: String(filters.offset) });
  for (const key of ["action", "actor_user_id", "entity_id", "since", "until"] as const) {
    if (filters[key]) query.set(key, api && ["since", "until"].includes(key) ? `${filters[key]}:00Z` : filters[key]);
  }
  return query.toString();
}
