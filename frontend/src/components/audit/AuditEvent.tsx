import { MutedText } from "@/components/ui/Text";
import {
  AuditEntry,
  auditActions,
  auditMetadataValue,
  entityLabels,
  metadataLabels,
} from "@/lib/audit";
import { formatUtcTimestamp } from "@/lib/date-time";
import styles from "./AuditEvent.module.css";

export function AuditEvent({ entry }: { entry: AuditEntry }) {
  const details = Object.entries(entry.metadata).filter(([key]) => Object.hasOwn(metadataLabels, key));
  const entityName = entry.entity_type === "USER_SESSION" ? entry.entity_id : entry.entity_name;
  return <article className={styles.event}>
    <header className={styles.header}><h2>{auditActions[entry.action] ?? "Evento histórico"}</h2>
      <time dateTime={entry.created_at}>{formatUtcTimestamp(entry.created_at)}</time></header>
    <p className={styles.actor}>Realizado por <strong>{entry.actor_name
      ?? (entry.actor_user_id ? "Usuario no disponible" : "Sistema")}</strong></p>
    <MutedText className={styles.resource}>{entityLabels[entry.entity_type] ?? "Recurso"}
      {entityName ? <> · <strong>{entityName}</strong></> : null}</MutedText>
    {details.length ? <details className={styles.details}><summary>Ver detalles del evento</summary>
      <dl>{details.map(([key, value]) => <div key={key}><dt>{metadataLabels[key]}</dt>
        <dd>{auditMetadataValue(entry, key, value)}</dd></div>)}</dl>
    </details> : null}
  </article>;
}
