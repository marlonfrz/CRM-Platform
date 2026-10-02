# CRM Platform

CRM web para gestionar el trabajo de una empresa o de un profesional independiente. El proyecto está en desarrollo y esta rama contiene la aplicación real, con API y base de datos PostgreSQL.

## Funcionalidades

- Organización con roles de propietario, administrador y empleado, y departamentos en modo empresa.
- Clientes con varias personas de contacto y asignación a empleados.
- Actividades, tareas pendientes y completadas, historial del cliente y paneles por rol.
- Auditoría de acciones relevantes y permisos comprobados en el backend.

## Tecnologías

- Frontend: Next.js, React y TypeScript.
- Backend: FastAPI, SQLAlchemy y Alembic.
- Datos: PostgreSQL. Docker Compose levanta también Mailpit para probar correos sin enviarlos.
- Calidad: ESLint, TypeScript, Ruff, mypy, Vitest y pytest.

## Ejecutarlo en local

Necesitas Docker con Docker Compose. Copia `.env.example` a `.env` y cambia las credenciales de ejemplo antes del primer arranque. Después:

```bash
docker compose up -d --build
docker compose exec backend alembic upgrade head
```

Abre [http://localhost:3000](http://localhost:3000). En el primer acceso podrás crear la organización y la cuenta propietaria. La API se documenta en [http://localhost:8000/docs](http://localhost:8000/docs) y los correos de desarrollo se ven en [http://localhost:8025](http://localhost:8025).

Los valores de `.env.example` son solo para desarrollo; no uses esas credenciales ni publiques PostgreSQL sin protección en producción.

## Comprobaciones

Para el frontend necesitas Node.js 22 o superior:

```bash
cd frontend
npm ci
npm run lint
npm run typecheck
npm test
npm run build
```

Para el backend necesitas Python 3.12 o superior y la base PostgreSQL de pruebas iniciada con `docker compose up -d database`:

```bash
cd backend
python -m pip install -e ".[dev]"
ruff check .
mypy app
pytest
```

Configura `TEST_DATABASE_URL` con las credenciales de tu PostgreSQL local y una base cuyo nombre termine en `_test`. Docker Compose crea `crm_platform_test` en el primer arranque de un volumen nuevo.
