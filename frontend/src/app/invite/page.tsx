import { Card } from "@/components/ui/Card";
import { Eyebrow, MutedText } from "@/components/ui/Text";

import { InviteForm } from "./invite-form";
import styles from "./page.module.css";

export default async function InvitePage({ searchParams }: { searchParams: Promise<{ token?: string }> }) {
  const { token } = await searchParams;
  return (
    <main className={styles.shell}>
      <Card className={styles.card}>
        <Eyebrow>Invitación</Eyebrow>
        <h1>Activa tu cuenta</h1>
        <MutedText>Elige una contraseña para acceder a tu espacio de trabajo.</MutedText>
        {token ? <InviteForm token={token} /> : <FormErrorMessage />}
      </Card>
    </main>
  );
}

function FormErrorMessage() {
  return <MutedText>El enlace de invitación no contiene un token válido.</MutedText>;
}
