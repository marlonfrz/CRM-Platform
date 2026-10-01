"use client";

import { FormEvent, useState } from "react";
import { SecretField } from "@/components/forms/SecretField";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { FormField } from "@/components/ui/FormField";
import { SelectField } from "@/components/ui/SelectField";
import { FormError, MutedText } from "@/components/ui/Text";
import { apiRequest } from "@/lib/client-api";
import {
  AIConfiguration,
  AIProvider,
  aiModels,
  aiProviders,
  customAIModelValue,
} from "@/lib/summaries";
import styles from "./AISettingsPanel.module.css";

const externalProviders = new Set<AIProvider>(["openai", "anthropic", "gemini"]);
const providerHelp: Record<AIProvider, string> = {
  disabled: "La generación de resúmenes queda desactivada para toda la organización.",
  openai: "Usa la API de OpenAI. La suscripción de ChatGPT y el uso de la API se facturan por separado.",
  anthropic: "Usa la API de Anthropic para modelos Claude.",
  gemini: "Usa la API de Google AI para modelos Gemini.",
  ollama: "Usa el servidor Ollama configurado por la instalación. No necesita guardar un token aquí.",
};

export function AISettingsPanel({ initialConfiguration, demo = false }: { initialConfiguration: AIConfiguration; demo?: boolean }) {
  const [saved, setSaved] = useState(initialConfiguration);
  const [provider, setProvider] = useState<AIProvider>(initialConfiguration.provider);
  const [model, setModel] = useState(initialConfiguration.model);
  const [apiKey, setApiKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const external = externalProviders.has(provider);
  const keepsExistingKey = saved.provider === provider && saved.has_api_key;
  const modelOptions = provider === "disabled" ? [] : demo ? [{ value: "Muestra preparada", label: "Muestra preparada" }] : aiModels[provider];
  const selectedModel = modelOptions.some((option) => option.value === model)
    ? model
    : customAIModelValue;

  function selectProvider(nextProvider: AIProvider) {
    setProvider(nextProvider);
    setModel(nextProvider === "disabled" ? "" : demo ? "Muestra preparada" : aiModels[nextProvider][0].value);
    setError("");
    setMessage("");
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true); setError(""); setMessage("");
    const payload: { provider: AIProvider; model: string; api_key?: string } = {
      provider, model: provider === "disabled" ? "" : model,
    };
    if (apiKey) payload.api_key = apiKey;
    try {
      const response = await apiRequest("/ai/configuration", {
        method: "PUT", body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const data = await response.json();
        setError(data.detail === "AI_API_KEY_REQUIRED"
          ? "Introduce un token para el proveedor seleccionado."
          : response.status === 403
            ? "Solo el propietario puede modificar estas opciones."
            : "No se pudo guardar la configuración de IA.");
        return;
      }
      const configuration = await response.json() as AIConfiguration;
      setSaved(configuration); setProvider(configuration.provider);
      setModel(configuration.model); setApiKey("");
      setMessage("Configuración guardada. El token no se volverá a mostrar.");
    } catch {
      setError("No se pudo conectar con el servidor.");
    } finally {
      setBusy(false);
    }
  }

  return <Card className={styles.panel}>
    <div><h2>Proveedor y credenciales</h2>
      <MutedText>Esta configuración se aplica a toda la organización y solo puede modificarla el propietario.</MutedText></div>
    <form className={styles.form} onSubmit={submit}>
      <SelectField label="Proveedor" value={provider} disabled={busy}
        onChange={(event) => selectProvider(event.target.value as AIProvider)}
        options={demo ? aiProviders.filter((item) => item.value === "disabled" || item.value === "ollama") : aiProviders} />
      <MutedText className={styles.providerHelp}>{demo ? "Los resúmenes se preparan con actividades sintéticas, sin consultar un proveedor externo." : providerHelp[provider]}</MutedText>
      {provider !== "disabled" ? <>
        <SelectField label="Modelo" value={selectedModel} disabled={busy}
          onChange={(event) => setModel(event.target.value === customAIModelValue ? "" : event.target.value)}
          options={demo ? modelOptions : [...modelOptions, { value: customAIModelValue, label: "Otro modelo · Opción avanzada" }]} />
        <MutedText className={styles.providerHelp}>La opción recomendada prioriza un coste y consumo moderados para generar resúmenes.</MutedText>
        {selectedModel === customAIModelValue ? <FormField label="Identificador avanzado" value={model}
          onChange={(event) => setModel(event.target.value)} required maxLength={100}
          pattern="[a-zA-Z0-9._:/-]+" placeholder="Ejemplo: nombre-del-modelo"
          hint="Utiliza esta opción únicamente si el proveedor te ha facilitado otro identificador." /> : null}
      </> : null}
      {external && !demo ? <SecretField label="Token de API" value={apiKey}
        onChange={(event) => setApiKey(event.target.value)} required={!keepsExistingKey}
        minLength={8} maxLength={2048} autoComplete="off"
        placeholder={keepsExistingKey ? "Déjalo vacío para conservar el token actual" : "Introduce el token del proveedor"}
        hint={keepsExistingKey ? "Ya existe un token cifrado. Solo escribe otro para sustituirlo." : "Se cifrará antes de guardarlo y no se mostrará de nuevo."} /> : null}
      {saved.source === "environment" ? <MutedText>La configuración actual procede del servidor. Al guardar, esta organización utilizará su propia configuración cifrada.</MutedText> : null}
      {error ? <FormError>{error}</FormError> : null}
      {message ? <p role="status" className={styles.success}>{message}</p> : null}
      <Button type="submit" disabled={busy}>{busy ? "Guardando…" : "Guardar opciones"}</Button>
    </form>
  </Card>;
}
