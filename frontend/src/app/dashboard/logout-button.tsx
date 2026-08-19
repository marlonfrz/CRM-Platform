"use client";

import { useRouter } from "next/navigation";

function csrfToken() {
  return document.cookie
    .split("; ")
    .find((item) => item.startsWith("crm_csrf="))
    ?.split("=")[1];
}

export function LogoutButton() {
  const router = useRouter();

  async function logout() {
    await fetch("/api/backend/auth/logout", {
      method: "POST",
      headers: { "X-CSRF-Token": decodeURIComponent(csrfToken() ?? "") },
    });
    router.replace("/login");
    router.refresh();
  }

  return <button className="secondary-button" onClick={logout}>Cerrar sesión</button>;
}
