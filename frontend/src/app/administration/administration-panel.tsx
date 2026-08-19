"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { FormField } from "@/components/ui/FormField";
import { FormError, MutedText } from "@/components/ui/Text";
import { apiRequest } from "@/lib/client-api";

import styles from "./administration-panel.module.css";

type Department = { id: string; name: string };
type AdministrationPanelProps = {
  canCreateDepartments: boolean;
  departments: Department[];
};

export function AdministrationPanel(props: AdministrationPanelProps) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [editingDepartment, setEditingDepartment] = useState<Department | null>(null);

  async function mutate(path: string, method: string, body?: object) {
    setError("");
    const response = await apiRequest(path, {
      method,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!response.ok) {
      setError(response.status === 403 ? "No tienes permiso para realizar esta acción." : "No se pudo guardar el cambio.");
      return false;
    }
    router.refresh();
    return true;
  }

  async function createDepartment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const name = new FormData(form).get("departmentName");
    if (await mutate("/admin/departments", "POST", { name })) form.reset();
  }

  async function saveDepartment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editingDepartment) return;
    const name = new FormData(event.currentTarget).get("departmentName");
    if (await mutate(`/admin/departments/${editingDepartment.id}`, "PATCH", { name })) {
      setEditingDepartment(null);
    }
  }

  async function removeDepartment(department: Department) {
    if (!window.confirm(`¿Eliminar el departamento ${department.name}?`)) return;
    await mutate(`/admin/departments/${department.id}`, "DELETE");
  }

  return (
    <div className={styles.stack}>
      {error ? <FormError>{error}</FormError> : null}
      <Card className={styles.departmentCard}>
        <div className={styles.sectionHeader}>
          <h2>Departamentos</h2>
          <span
            aria-label={`${props.departments.length} departamentos`}
            className={styles.count}
          >
            {props.departments.length}
          </span>
        </div>
        {props.canCreateDepartments ? (
          <form className={`${styles.form} ${styles.createForm}`} onSubmit={createDepartment}>
            <FormField label="Nuevo departamento" name="departmentName" required maxLength={120} />
            <Button type="submit">Crear</Button>
          </form>
        ) : null}
        <div className={styles.departmentList}>
          {props.departments.length === 0 ? <MutedText className={styles.empty}>Todavía no hay departamentos disponibles.</MutedText> : null}
          {props.departments.map((department) => (
            <div className={styles.department} key={department.id}>
              {editingDepartment?.id === department.id ? (
                <form className={styles.form} onSubmit={saveDepartment}>
                  <FormField label="Nombre" name="departmentName" defaultValue={department.name} required maxLength={120} />
                  <Button type="submit">Guardar</Button>
                  <Button type="button" variant="quiet" onClick={() => setEditingDepartment(null)}>Cancelar</Button>
                </form>
              ) : (
                <><strong>{department.name}</strong><div className={styles.actions}>
                  <Button type="button" variant="quiet" onClick={() => setEditingDepartment(department)}>Editar</Button>
                  <Button type="button" variant="danger" onClick={() => removeDepartment(department)}>Eliminar</Button>
                </div></>
              )}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
