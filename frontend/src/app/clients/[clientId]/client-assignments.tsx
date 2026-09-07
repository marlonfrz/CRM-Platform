"use client";

import { FormEvent, useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { SelectField } from "@/components/ui/SelectField";
import { FormError, MutedText } from "@/components/ui/Text";
import { apiRequest } from "@/lib/client-api";
import type { AssignmentTeam } from "@/lib/clients";

import styles from "./client-assignments.module.css";

type Props = { clientId: string; team: AssignmentTeam; scoped: boolean };

export function ClientAssignments({ clientId, team, scoped }: Props) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [removing, setRemoving] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [refreshing, startTransition] = useTransition();
  const inFlight = useRef(false);
  const busy = submitting || refreshing;

  async function mutate(userId: string, remove: boolean) {
    if (inFlight.current || busy) return;
    inFlight.current = true;
    setSubmitting(true);
    setError("");
    setMessage("");
    try {
      const response = await apiRequest(
        `/clients/${clientId}/assignments${remove ? `/${userId}` : ""}`,
        { method: remove ? "DELETE" : "POST", body: remove ? undefined : JSON.stringify({ user_id: userId }) },
      );
      if (response.status === 401) {
        router.push("/login");
        return;
      }
      if (!response.ok) {
        const errors: Record<number, string> = {
          403: "No tienes permiso para gestionar esta asignación.",
          404: "El cliente, empleado o asignación ya no está disponible.",
          409: "El empleado ya está asignado o ya no reúne los requisitos para asignarlo.",
        };
        setError(errors[response.status] ?? "No se pudo guardar la asignación. Inténtalo de nuevo.");
      } else {
        setRemoving(null);
        setMessage(remove ? "Asignación retirada." : "Cliente asignado correctamente.");
      }
      startTransition(() => router.refresh());
    } catch {
      setError("No se pudo conectar. Comprueba tu conexión y vuelve a intentarlo.");
    } finally {
      inFlight.current = false;
      setSubmitting(false);
    }
  }

  function assign(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const userId = new FormData(event.currentTarget).get("userId");
    if (typeof userId === "string" && userId) void mutate(userId, false);
  }

  return (
    <Card className={styles.card} aria-label="Equipo asignado" aria-busy={busy}>
      <header className={styles.header}>
        <h2>Equipo asignado</h2>
        {scoped ? <MutedText>Empleados de los departamentos que administras.</MutedText> : null}
      </header>
      <form className={styles.form} onSubmit={assign}>
        <SelectField
          key={team.available.map((user) => user.user_id).join(",")}
          label="Empleado" name="userId" required defaultValue="" disabled={busy || !team.available.length}
          options={[
            { label: team.available.length ? "Selecciona un empleado" : "No hay empleados disponibles", value: "" },
            ...team.available.map((user) => ({ label: user.full_name, value: user.user_id })),
          ]}
        />
        <Button type="submit" disabled={busy || !team.available.length}>Asignar cliente</Button>
      </form>
      {error ? <FormError>{error}</FormError> : null}
      <p className={styles.message} role="status">{message}</p>
      <ul className={styles.list}>
        {team.assigned.map((user) => (
          <li className={styles.row} key={user.user_id}>
            <div className={styles.identity}>
              <strong>{user.full_name}</strong>
              {user.status !== "ACTIVE" ? <span>{user.status === "DISABLED" ? "Desactivado" : "Pendiente de activación"}</span> : null}
            </div>
            {removing === user.user_id ? (
              <div className={styles.confirm}>
                <p>¿Retirar la asignación de {user.full_name}? El cliente y sus contactos se conservarán.</p>
                <div className={styles.actions}>
                  <Button type="button" variant="danger" disabled={busy} onClick={() => void mutate(user.user_id, true)}>Confirmar retirada</Button>
                  <Button type="button" variant="quiet" disabled={busy} onClick={() => setRemoving(null)}>Cancelar</Button>
                </div>
              </div>
            ) : (
              <Button type="button" variant="quiet" disabled={busy} aria-label={`Retirar asignación de ${user.full_name}`} onClick={() => setRemoving(user.user_id)}>Retirar asignación</Button>
            )}
          </li>
        ))}
      </ul>
      {!team.assigned.length ? <MutedText className={styles.empty}>Todavía no hay empleados asignados{scoped ? " dentro de tu alcance" : ""}.</MutedText> : null}
    </Card>
  );
}
