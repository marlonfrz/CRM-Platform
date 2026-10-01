"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { apiRequest } from "@/lib/client-api";

const renewalIntervalMilliseconds = 5 * 60 * 1000;

export function SessionHeartbeat() {
  const router = useRouter();

  useEffect(() => {
    let active = true;
    let renewing = false;

    async function renew() {
      if (!active || renewing || document.visibilityState !== "visible") return;
      renewing = true;
      try {
        const response = await apiRequest("/auth/me");
        if (response.status === 401 && active) router.replace("/login");
      } catch {
        return;
      } finally {
        renewing = false;
      }
    }

    void renew();
    const interval = window.setInterval(() => void renew(), renewalIntervalMilliseconds);
    const handleVisibility = () => void renew();
    document.addEventListener("visibilitychange", handleVisibility);
    window.addEventListener("focus", handleVisibility);
    return () => {
      active = false;
      window.clearInterval(interval);
      document.removeEventListener("visibilitychange", handleVisibility);
      window.removeEventListener("focus", handleVisibility);
    };
  }, [router]);

  return null;
}
