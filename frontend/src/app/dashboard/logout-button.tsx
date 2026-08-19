"use client";

import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";

function csrfToken() {
  return document.cookie
    .split("; ")
    .find((item) => item.startsWith("crm_csrf="))
    ?.split("=")[1];
}

export function LogoutButton({ className = "" }: { className?: string }) {
  const router = useRouter();

  async function logout() {
    await fetch("/api/backend/auth/logout", {
      method: "POST",
      headers: { "X-CSRF-Token": decodeURIComponent(csrfToken() ?? "") },
    });
    router.replace("/login");
    router.refresh();
  }

  return <Button className={className} variant="secondary" onClick={logout}>Cerrar sesión</Button>;
}
