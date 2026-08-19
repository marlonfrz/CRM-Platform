"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { FormField } from "@/components/ui/FormField";
import { SelectField } from "@/components/ui/SelectField";
import { FormError, MutedText } from "@/components/ui/Text";
import { apiRequest } from "@/lib/client-api";

import styles from "./user-administration.module.css";

type Department = { id: string; name: string };
type User = {
  id: string;
  email: string;
  full_name: string;
  role: "OWNER" | "ADMIN" | "EMPLOYEE";
  status: "PENDING" | "ACTIVE" | "DISABLED";
  department_ids: string[];
};

type Props = {
  actorRole: User["role"];
  currentUserId: string;
  departments: Department[];
  users: User[];
};

const roleLabels = { OWNER: "Propietario", ADMIN: "Administrador", EMPLOYEE: "Empleado" };
const statusLabels = { PENDING: "Invitación pendiente", ACTIVE: "Activo", DISABLED: "Desactivado" };

export function UserAdministration({ actorRole, currentUserId, departments, users }: Props) {
  const router = useRouter();
  const [editing, setEditing] = useState<User | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");

  async function mutate(path: string, method: string, body?: object) {
    setError("");
    const response = await apiRequest(path, { method, body: body ? JSON.stringify(body) : undefined });
    if (!response.ok) {
      setError(response.status === 409 ? "El cambio entra en conflicto con el estado actual." : "No se pudo completar la operación.");
      return false;
    }
    router.refresh();
    return true;
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const body = {
      email: data.get("email"),
      full_name: data.get("fullName"),
      role: data.get("role"),
      department_ids: data.getAll("departments"),
    };
    const success = editing
      ? await mutate(`/admin/users/${editing.id}`, "PATCH", body)
      : await mutate("/admin/users", "POST", body);
    if (success) { setEditing(null); setShowForm(false); form.reset(); }
  }

  function startEditing(user: User) {
    setEditing(user);
    setShowForm(true);
    setError("");
  }

  async function disable(user: User) {
    if (!window.confirm(`¿Desactivar a ${user.full_name}? Se cerrarán todas sus sesiones.`)) return;
    await mutate(`/admin/users/${user.id}/disable`, "POST");
  }

  const roleOptions = actorRole === "OWNER"
    ? [{ label: "Administrador", value: "ADMIN" }, { label: "Empleado", value: "EMPLOYEE" }]
    : [{ label: "Empleado", value: "EMPLOYEE" }];

  return (
    <Card className={styles.card}>
      <div className={styles.header}>
        <h2>Usuarios</h2>
        <Button type="button" onClick={() => { setEditing(null); setShowForm((visible) => !visible); }}>
          {showForm && !editing ? "Cerrar" : "Añadir usuario"}
        </Button>
      </div>
      {error ? <FormError>{error}</FormError> : null}
      {showForm ? (
        <form className={styles.form} key={editing?.id ?? "new"} onSubmit={save}>
          <div className={styles.formGrid}>
            <FormField label="Nombre completo" name="fullName" defaultValue={editing?.full_name} required maxLength={200} />
            <FormField label="Correo" name="email" type="email" defaultValue={editing?.email} disabled={Boolean(editing)} required />
            <SelectField label="Rol" name="role" defaultValue={editing?.role === "OWNER" ? "ADMIN" : editing?.role ?? "EMPLOYEE"} options={roleOptions} />
          </div>
          <fieldset className={styles.departments}>
            <legend>Departamentos</legend>
            <span className={styles.checkboxGrid}>
              {departments.map((department) => (
                <label className={styles.checkbox} key={department.id}>
                  <input name="departments" type="checkbox" value={department.id} defaultChecked={editing?.department_ids.includes(department.id)} />
                  {department.name}
                </label>
              ))}
            </span>
          </fieldset>
          <div className={styles.formActions}>
            <Button type="submit">{editing ? "Guardar cambios" : "Enviar invitación"}</Button>
            <Button type="button" variant="quiet" onClick={() => { setEditing(null); setShowForm(false); }}>Cancelar</Button>
          </div>
        </form>
      ) : null}
      <div className={styles.userList}>
        {users.length === 0 ? <MutedText className={styles.empty}>Todavía no hay usuarios disponibles.</MutedText> : null}
        {users.map((user) => {
          const names = departments.filter((item) => user.department_ids.includes(item.id)).map((item) => item.name);
          const isCurrentUser = user.id === currentUserId;
          const canManageUser = !isCurrentUser && user.role !== "OWNER";
          return (
            <div className={styles.user} key={user.id}>
              <div className={styles.identity}><strong>{user.full_name}</strong><span>{user.email}</span></div>
              <span className={`${styles.badge} ${user.status === "PENDING" ? styles.statusPending : ""} ${user.status === "DISABLED" ? styles.statusDisabled : ""}`}>{statusLabels[user.status]}</span>
              <div><strong>{roleLabels[user.role]}</strong><div className={styles.departmentNames}>{names.join(", ") || "Sin departamentos"}</div></div>
              {canManageUser ? <div className={styles.actions}>
                <Button type="button" variant="quiet" onClick={() => startEditing(user)}>Editar</Button>
                {user.status === "PENDING" ? <Button type="button" variant="quiet" onClick={() => mutate(`/admin/users/${user.id}/invitation`, "POST")}>Reenviar</Button> : null}
                {user.status === "ACTIVE" ? <Button type="button" variant="danger" onClick={() => disable(user)}>Desactivar</Button> : null}
                {user.status === "DISABLED" ? <Button type="button" onClick={() => mutate(`/admin/users/${user.id}/activate`, "POST")}>Activar</Button> : null}
              </div> : null}
            </div>
          );
        })}
      </div>
    </Card>
  );
}
