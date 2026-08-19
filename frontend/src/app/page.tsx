import { redirect } from "next/navigation";

import { isInstallationInitialized } from "@/lib/setup";

export default async function HomePage() {
  if (!(await isInstallationInitialized())) redirect("/setup");
  redirect("/dashboard");
}
