import Link from "next/link";

import { Card } from "@/components/ui/Card";
import { MutedText } from "@/components/ui/Text";

export default function ClientNotFound() {
  return (
    <Card>
      <h1>Cliente no disponible</h1>
      <MutedText>El cliente no existe o ya no tienes acceso a su ficha.</MutedText>
      <Link href="/clients">Volver a mis clientes</Link>
    </Card>
  );
}
