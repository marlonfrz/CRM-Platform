"use client";

import { useState } from "react";

import { useActivityMutation } from "@/components/activities/useActivityMutation";
import { Button } from "@/components/ui/Button";
import { FormError, MutedText } from "@/components/ui/Text";
import { Activity, activityDate, activityTimestamp } from "@/lib/activities";

import { ActivityForm } from "./activity-form";
import styles from "./activity-entry.module.css";

type Props = {
  clientId: string;
  activity: Activity;
};

export function ActivityEntry({ clientId, activity }: Props) {
  const [editing, setEditing] = useState(false);
  const [confirming, setConfirming] = useState<"COMPLETE" | "DELETE" | null>(null);
  const [message, setMessage] = useState("");
  const { mutate, error, busy } = useActivityMutation();
  const pending = activity.status === "PENDING";
  const heading = activity.title || activity.activity_type_name;

  async function complete() {
    if (await mutate(`/clients/${clientId}/activities/${activity.id}/complete`, "POST")) {
      setConfirming(null);
      setMessage("Actividad completada.");
    }
  }

  async function remove(scope: "THIS" | "THIS_AND_FOLLOWING") {
    if (await mutate(
      `/clients/${clientId}/activities/${activity.id}?scope=${scope}`,
      "DELETE",
    )) {
      setConfirming(null);
      setMessage("Actividad eliminada.");
    }
  }

  return (
    <article className={styles.entry}>
      <header className={styles.header}>
        <div>
          <span className={styles.type}>{activity.activity_type_name}</span>
          <h3>{heading}</h3>
          <MutedText>
            {activity.assigned_to_name}
            {activity.department_name ? ` · ${activity.department_name}` : ""}
          </MutedText>
        </div>
        <span className={pending ? styles.pending : styles.completed}>
          {pending ? "Pendiente" : "Completada"}
        </span>
      </header>

      {editing ? (
        <ActivityForm clientId={clientId} activity={activity}
          onDone={(changed) => {
            setEditing(false);
            if (changed) setMessage("Cambios guardados.");
          }} />
      ) : (
        <>
          <p className={styles.content}>{activity.description}</p>
          <div className={styles.dates}>
            <MutedText>Programada: {activityDate(activity.scheduled_for)}</MutedText>
            {activity.completed_at ? (
              <MutedText>Completada: {activityTimestamp(activity.completed_at)}</MutedText>
            ) : null}
            {activity.schedule_id ? <span className={styles.recurring}>Recurrente</span> : null}
          </div>
          {activity.next_action ? (
            <div className={styles.nextAction}>
              <strong>Próxima acción</strong>
              <p className={styles.content}>{activity.next_action}</p>
            </div>
          ) : null}
          <footer className={styles.footer}>
            <MutedText>
              Registrada: {activityTimestamp(activity.created_at)}
              {activity.updated_at !== activity.created_at
                ? ` · Actualizada: ${activityTimestamp(activity.updated_at)}` : ""}
            </MutedText>
            <div className={styles.actions}>
              {confirming === "COMPLETE" ? (
                <>
                  <span>¿Marcar como completada?</span>
                  <Button type="button" disabled={busy} onClick={() => void complete()}>Confirmar</Button>
                  <Button type="button" variant="quiet" disabled={busy}
                    onClick={() => setConfirming(null)}>Cancelar</Button>
                </>
              ) : confirming === "DELETE" ? (
                <>
                  <span>¿Qué quieres eliminar?</span>
                  <Button type="button" variant="danger" disabled={busy}
                    onClick={() => void remove("THIS")}>Solo esta</Button>
                  {activity.schedule_id ? (
                    <Button type="button" variant="danger" disabled={busy}
                      onClick={() => void remove("THIS_AND_FOLLOWING")}>
                      Esta y las siguientes
                    </Button>
                  ) : null}
                  <Button type="button" variant="quiet" disabled={busy}
                    onClick={() => setConfirming(null)}>Cancelar</Button>
                </>
              ) : (
                <>
                  {pending && activity.can_edit ? (
                    <Button type="button" disabled={busy}
                      onClick={() => { setMessage(""); setConfirming("COMPLETE"); }}>
                      Completar
                    </Button>
                  ) : null}
                  {activity.can_edit ? (
                    <Button type="button" variant="quiet" disabled={busy}
                      onClick={() => { setMessage(""); setEditing(true); }}>Editar</Button>
                  ) : null}
                  {activity.can_delete ? (
                    <Button type="button" variant="danger" disabled={busy}
                      onClick={() => { setMessage(""); setConfirming("DELETE"); }}>Eliminar</Button>
                  ) : null}
                </>
              )}
            </div>
          </footer>
        </>
      )}
      {error ? <FormError>{error}</FormError> : null}
      {message ? <p role="status">{message}</p> : null}
    </article>
  );
}
