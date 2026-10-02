# CRM Platform · Demo

Esta rama presenta el CRM con el mismo frontend Next.js y las mismas rutas de la aplicación, pero con datos ficticios en memoria. No necesita PostgreSQL, el backend ni un proveedor externo de IA. Los cambios que hagas durante la visita son temporales y no afectan a una base de datos.

## Qué puedes explorar

- Clientes con varios contactos, actividad, tareas e historial.
- Organización con usuarios, roles y departamentos.
- Paneles, auditoría y resúmenes de actividad preparados localmente.

## Ejecutar la demo

Con Node.js 22 o superior:

```bash
cd frontend
npm ci
npm run demo
```

Abre [http://127.0.0.1:4173](http://127.0.0.1:4173). También puedes usar Docker Compose desde la raíz:

```bash
docker compose -f compose.demo.yaml up --build -d
```

Cada navegador recibe una sesión temporal de datos. Al reiniciar Next.js o tras 24 horas, vuelve el estado inicial. La generación de resúmenes es local y no consume tokens de proveedores de IA.

## Comprobaciones

```bash
cd frontend
npm run lint
npm run typecheck
npm test
npm run demo:build
```

El despliegue de esta rama solo necesita el contenedor Next.js. Aunque no haya costes de base de datos ni de API de IA, las visitas consumen recursos del servidor donde se publique. El CRM completo con PostgreSQL se mantiene en `main`.
