"use client";

import { useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { apiRequest } from "@/lib/client-api";

export function useActivityMutation() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [refreshing, startTransition] = useTransition();
  const inFlight = useRef(false);
  const busy = saving || refreshing;

  async function mutate(path: string, method: "POST" | "DELETE") {
    if (inFlight.current || busy) return false;
    inFlight.current = true;
    setSaving(true);
    setError("");
    try {
      const response = await apiRequest(path, { method });
      if (response.status === 401) { router.push("/login"); return false; }
      if (!response.ok) {
        const errors: Record<number, string> = {
          403: "No tienes permiso para gestionar esta actividad.",
          404: "La actividad ya no está disponible.",
          409: "La actividad ya cambió de estado.",
        };
        setError(errors[response.status] ?? "No se pudo realizar la acción.");
        return false;
      }
      startTransition(() => router.refresh());
      return true;
    } catch {
      setError("No se pudo conectar con el servidor.");
      return false;
    } finally {
      inFlight.current = false;
      setSaving(false);
    }
  }
  return { mutate, busy, error };
}
