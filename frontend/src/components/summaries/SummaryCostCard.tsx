import { formatEstimatedUsd, type SummaryResult } from "@/lib/summaries";
import styles from "./SummaryCostCard.module.css";

export function SummaryCostCard({ result }: { result: SummaryResult }) {
  const noProviderCall = result.cached || result.sections.length === 0 || result.provider === "Demo";
  const cost = noProviderCall || result.provider === "ollama"
    ? 0
    : result.usage?.estimated_cost_usd;

  return <section className={styles.card} aria-label="Coste de la consulta">
    <h2>Coste de esta consulta</h2>
    <strong className={styles.amount}>{cost == null ? "No disponible" : formatEstimatedUsd(cost)}</strong>
    {noProviderCall ? <p>No se ha hecho una nueva llamada al proveedor.</p>
      : <>
        {result.usage ? <p>{result.usage.input_tokens} tokens de entrada · {result.usage.output_tokens} de salida</p>
          : <p>El proveedor no informó del consumo de tokens.</p>}
        <p>{result.provider === "ollama" ? "Sin coste de API; el equipo local sí consume recursos."
          : cost == null ? "No hay una tarifa verificada para calcular el importe de este modelo."
          : "Importe orientativo calculado con los tokens reportados; la factura puede variar."}</p>
      </>}
  </section>;
}
