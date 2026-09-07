"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { MutedText } from "@/components/ui/Text";
import { Activity, activityTimestamp, activityTypes } from "@/lib/activities";
import { ActivityForm } from "./activity-form";
import styles from "./activity-entry.module.css";

export function ActivityEntry({ clientId, activity }: { clientId: string; activity: Activity }) {
  const [editing, setEditing] = useState(false);
  const [saved, setSaved] = useState(false);
  return (
    <article className={styles.entry}>
      <header className={styles.header}>
        <div>
          <h3>{activityTypes[activity.type]}</h3>
          <MutedText>{activity.user_name}{activity.department_name ? ` · ${activity.department_name}` : ""}</MutedText>
        </div>
        <time dateTime={activity.occurred_at}>{activityTimestamp(activity.occurred_at)}</time>
      </header>
      {saved ? <p role="status">Corrección guardada.</p> : null}
      {editing && activity.can_edit ? <ActivityForm clientId={clientId} departments={[]} activity={activity} onDone={(changed) => { setEditing(false); setSaved(!!changed); }} /> : (
        <>
          <p className={styles.content}>{activity.description}</p>
          {activity.next_action ? <div className={styles.nextAction}><strong>Próxima acción</strong><p className={styles.content}>{activity.next_action}</p></div> : null}
          <footer className={styles.footer}>
            <MutedText>Registrada: {activityTimestamp(activity.created_at)}{activity.updated_at !== activity.created_at ? ` · Corregida: ${activityTimestamp(activity.updated_at)}` : ""}</MutedText>
            {activity.can_edit ? <Button type="button" variant="quiet" onClick={() => { setSaved(false); setEditing(true); }}>Corregir actividad</Button> : null}
          </footer>
        </>
      )}
    </article>
  );
}
