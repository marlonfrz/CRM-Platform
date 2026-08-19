"use client";

import { useRouter } from "next/navigation";

import { apiRequest } from "@/lib/client-api";
import { Button } from "@/components/ui/Button";

export function LogoutButton({ className = "" }: { className?: string }) {
  const router = useRouter();

  async function logout() {
    await apiRequest("/auth/logout", { method: "POST" });
    router.replace("/login");
    router.refresh();
  }

  return <Button className={className} variant="secondary" onClick={logout}>Cerrar sesión</Button>;
}
