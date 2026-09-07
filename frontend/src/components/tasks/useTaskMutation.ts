"use client";

import { useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { apiRequest } from "@/lib/client-api";

export function useTaskMutation() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [refreshing, startTransition] = useTransition();
  const inFlight = useRef(false);
  const busy = saving || refreshing;

  async function mutate(path: string, method: string, payload?: () => object) {
    if (inFlight.current || busy) return false;
    inFlight.current = true;
    setSaving(true);
    setError("");
    try {
      const response = await apiRequest(path, { method, body: payload ? JSON.stringify(payload()) : undefined });
      if (response.status === 401) { router.push("/login"); return false; }
      if (!response.ok) {
        const errors: Record<number, string> = {
          403: "No tienes permiso o el responsable ya no cumple los requisitos de acceso.",
          404: "La tarea, el cliente o el responsable ya no están disponibles.",
          409: "La tarea ya está completada o falta elegir un departamento disponible.",
          422: "Revisa los campos: título obligatorio, fecha válida y longitud de los textos.",
        };
        setError(errors[response.status] ?? "No se pudo guardar la tarea. Inténtalo de nuevo.");
        return false;
      }
      startTransition(() => router.refresh());
      return true;
    } catch {
      setError("No se pudo conectar o la fecha no es válida. Revisa los datos e inténtalo de nuevo.");
      return false;
    } finally {
      inFlight.current = false;
      setSaving(false);
    }
  }
  return { mutate, busy, error };
}
