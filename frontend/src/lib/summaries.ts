export type AIProvider = "disabled" | "ollama" | "openai" | "anthropic" | "gemini";
export type SummaryOptions = { enabled: boolean; provider: AIProvider; model: string; external: boolean; departments: { id: string; name: string }[] };
export type AIConfiguration = {
  provider: AIProvider; model: string; has_api_key: boolean; source: "organization" | "environment";
};
export const aiProviders: { value: AIProvider; label: string }[] = [
  { value: "disabled", label: "Desactivada" },
  { value: "openai", label: "OpenAI (ChatGPT API)" },
  { value: "anthropic", label: "Anthropic (Claude API)" },
  { value: "gemini", label: "Google Gemini API" },
  { value: "ollama", label: "Ollama local" },
];
export const customAIModelValue = "__custom__";
export const aiModels: Record<Exclude<AIProvider, "disabled">, { value: string; label: string }[]> = {
  openai: [
    { value: "gpt-5.6-luna", label: "GPT-5.6 Luna · Menor coste (recomendado)" },
    { value: "gpt-5.6-terra", label: "GPT-5.6 Terra · Mayor capacidad" },
  ],
  anthropic: [
    { value: "claude-haiku-4-5-20251001", label: "Claude Haiku 4.5 · Rápido y económico (recomendado)" },
    { value: "claude-sonnet-5", label: "Claude Sonnet 5 · Mayor capacidad" },
  ],
  gemini: [
    { value: "gemini-3.5-flash-lite", label: "Gemini 3.5 Flash-Lite · Menor coste (recomendado)" },
    { value: "gemini-3.8-flash", label: "Gemini 3.8 Flash · Mayor capacidad" },
  ],
  ollama: [
    { value: "llama3.2:1b", label: "Llama 3.2 1B · Pruebas locales (recomendado)" },
    { value: "qwen3.5:2b", label: "Qwen 3.5 2B · Más calidad, más lento" },
    { value: "qwen3.5:4b", label: "Qwen 3.5 4B · Para equipos potentes" },
  ],
};
export function aiProviderLabel(provider: AIProvider) {
  return aiProviders.find((item) => item.value === provider)?.label ?? provider;
}
export type SummarySource = {
  id: string; client_id: string; client_name: string; activity_type_name: string;
  title: string | null; description: string; status: "PENDING" | "COMPLETED";
  scheduled_for: string; occurred_at: string | null;
};
export type SummaryResult = {
  request_id: string | null; generated_at: string; provider: string; model: string; cached?: boolean;
  usage?: { input_tokens: number; output_tokens: number; estimated_cost_usd: number | null } | null;
  sections: { department_id: string | null; department_name: string | null;
    content: { summary: string; pending_actions: string[]; source_ids: string[] };
    sources: SummarySource[] }[];
};
export type SummaryLatest = {
  generated_at: string; since: string; until: string; provider: string; model: string;
  section: SummaryResult["sections"][number];
};
export function formatEstimatedUsd(amount: number) {
  return new Intl.NumberFormat("es-ES", {
    style: "currency", currency: "USD", minimumFractionDigits: 4, maximumFractionDigits: 6,
  }).format(amount);
}
export const summaryErrors: Record<string, string> = {
  AI_NOT_CONFIGURED: "La IA no está habilitada. El propietario debe acordar su configuración con el responsable de la instalación.",
  AI_CONTEXT_TOO_LARGE: "Hay demasiada información. Reduce el periodo o selecciona un cliente o departamento.",
  AI_RATE_LIMITED: "Se ha solicitado otro resumen recientemente. Espera unos segundos antes de reintentar.",
  AI_INVALID_OUTPUT: "El proveedor no devolvió un resumen válido. No se muestra una respuesta parcial.",
  AI_PROVIDER_UNAVAILABLE: "No se pudo consultar el proveedor. Revisa su disponibilidad y configuración.",
  AI_ACCESS_CHANGED: "Tu sesión o permisos han cambiado. Vuelve a acceder antes de generar otro resumen.",
  AI_TIMEOUT: "El proveedor superó el tiempo de espera. Reduce el periodo o inténtalo más tarde.",
};
