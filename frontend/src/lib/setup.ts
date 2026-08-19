export async function isInstallationInitialized() {
  const response = await fetch(
    `${process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000"}/api/v1/setup/status`,
    { cache: "no-store" },
  );
  if (!response.ok) throw new Error("Setup status could not be loaded");
  const payload = (await response.json()) as { initialized: boolean };
  return payload.initialized;
}
