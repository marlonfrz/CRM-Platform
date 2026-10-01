"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { FormField } from "@/components/ui/FormField";
import { SelectField } from "@/components/ui/SelectField";
import { MutedText } from "@/components/ui/Text";
import { apiRequest } from "@/lib/client-api";
import { SummaryLatest, SummaryOptions, SummaryResult as Result, aiProviderLabel, summaryErrors } from "@/lib/summaries";
import { LatestSummaries } from "./LatestSummaries";
import { SummaryResult } from "./SummaryResult";
import styles from "./SummaryPanel.module.css";

type Props = { options: SummaryOptions; individual: boolean; clientId?: string; initialSince: string; initialUntil: string; demo?: boolean };

export function SummaryPanel({ options, individual, clientId, initialSince, initialUntil, demo = false }: Props) {
  const scope = clientId ? "CLIENT" : individual ? "ORGANIZATION" : "DEPARTMENT";
  const [departmentId, setDepartmentId] = useState(options.departments[0]?.id ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [resultPeriod, setResultPeriod] = useState<{ since: string; until: string } | null>(null);
  const [latestState, setLatestState] = useState<{ key: string; items: SummaryLatest[]; error: string }>(
    { key: "", items: [], error: "" },
  );
  const [latestVersion, setLatestVersion] = useState(0);
  const pending = useRef(false);
  const router = useRouter();
  const query = new URLSearchParams({ scope });
  if (scope === "CLIENT" && clientId) query.set("client_id", clientId);
  if (scope === "DEPARTMENT") query.set("department_id", departmentId);
  const latestQuery = query.toString();
  const latestKey = `${latestQuery}:${latestVersion}`;
  const hasTarget = scope !== "DEPARTMENT" || !!departmentId;
  const loadingLatest = hasTarget && latestState.key !== latestKey;
  useEffect(() => {
    if (!hasTarget) return;
    const controller = new AbortController();
    apiRequest(`/ai/summaries/latest?${latestQuery}`, { signal: controller.signal })
      .then(async (response) => {
        if (response.status === 401) { router.push("/login"); return; }
        if (!response.ok) throw new Error("Latest summaries unavailable");
        const items = await response.json() as SummaryLatest[];
        if (!controller.signal.aborted) setLatestState({ key: latestKey, items, error: "" });
      })
      .catch(() => {
        if (!controller.signal.aborted) setLatestState({
          key: latestKey, items: [], error: "No se pudieron cargar los resúmenes guardados.",
        });
      });
    return () => controller.abort();
  }, [hasTarget, latestKey, latestQuery, router]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending.current) return;
    const form = new FormData(event.currentTarget);
    const period = { since: `${form.get("since")}:00Z`, until: `${form.get("until")}:00Z` };
    pending.current = true; setBusy(true); setError(""); setResult(null);
    try {
      const response = await apiRequest("/ai/summaries", { method: "POST", body: JSON.stringify({
        scope, client_id: clientId ?? null,
        department_id: scope === "DEPARTMENT" ? departmentId : null,
        ...period,
      }) });
      if (response.status === 401) { router.push("/login"); return; }
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        setError(typeof data?.detail === "string" && summaryErrors[data.detail] ? summaryErrors[data.detail]
          : response.status === 403 ? "No tienes permiso para generar este resumen."
          : response.status >= 500 ? "El servidor no pudo generar el resumen. Inténtalo más tarde o avisa al administrador."
          : "No se pudo generar el resumen. Revisa las fechas y el alcance seleccionado.");
        return;
      }
      setResult(await response.json() as Result);
      setResultPeriod(period);
      setLatestVersion((current) => current + 1);
    } catch { setError("No se pudo conectar. Comprueba la conexión e inténtalo de nuevo."); }
    finally { pending.current = false; setBusy(false); }
  }
  return <Card className={styles.panel}>
    {!options.enabled ? <p role="status">{summaryErrors.AI_NOT_CONFIGURED}</p> : <MutedText>{demo ? `Modelo: ${options.model}` : `Proveedor: ${aiProviderLabel(options.provider)} · Modelo: ${options.model}`}</MutedText>}
    <MutedText>Se utilizan nombres de clientes, tipos, fechas, descripciones y próximas acciones de actividades autorizadas. No se envían fichas de contacto ni datos de usuarios. Los textos libres pueden contener información privada y, si el proveedor es externo, se enviarán según la configuración elegida por el propietario.</MutedText>
    <form onSubmit={submit} onChange={() => setResult(null)} className={styles.form}>
      <fieldset disabled={!options.enabled || busy} className={styles.fields}>
        {scope === "DEPARTMENT" ? <SelectField label="Departamento" name="department_id" required
          value={departmentId} onChange={(event) => setDepartmentId(event.target.value)} options={[
          { value: "", label: "Selecciona un departamento" }, ...options.departments.map((item) => ({ value: item.id, label: item.name })),
        ]} /> : null}
        <FormField label="Desde (UTC)" name="since" type="datetime-local" defaultValue={initialSince} required />
        <FormField label="Hasta (UTC, inclusive)" name="until" type="datetime-local" defaultValue={initialUntil} required />
        <Button type="submit">{busy ? "Generando resumen…" : "Generar resumen"}</Button>
      </fieldset>
    </form>
    {error ? <p role="alert" className={styles.error}>{error}</p> : null}
    {busy ? <MutedText role="status">Consultando únicamente el alcance seleccionado. El resultado no se guarda como actividad ni modifica tareas.</MutedText> : null}
    {result ? <SummaryResult result={result} period={resultPeriod} />
      : <LatestSummaries items={latestState.key === latestKey ? latestState.items : []}
        loading={loadingLatest} error={latestState.key === latestKey ? latestState.error : ""} />}
  </Card>;
}
