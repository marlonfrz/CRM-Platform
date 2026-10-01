# Producción y operación

## Alcance

Cada empresa recibe una instalación independiente con su propio proyecto Compose, base de datos, volúmenes, dominio y secretos. Las imágenes de frontend y backend son artefactos comunes e inmutables de una release; no contienen configuración ni datos del cliente.

La imagen backend instala únicamente `requirements.runtime.lock`; las herramientas de test, lint y tipado permanecen fuera del artefacto entregado.

El único servicio publicado es Caddy en los puertos 80 y 443. Caddy termina HTTPS y reenvía a Next.js. Frontend, FastAPI y PostgreSQL se comunican por redes Docker privadas; PostgreSQL y FastAPI no publican puertos del host. El backend conserva una red saliente separada para SMTP y proveedores de IA.

## Requisitos del servidor

- Linux mantenido y actualizado;
- Docker Engine con Docker Compose;
- dominio con registros DNS dirigidos al servidor;
- puertos 80 y 443 permitidos por el firewall;
- acceso administrativo SSH restringido;
- registry accesible desde el servidor;
- almacenamiento externo cifrado para backups.

La instalación no abre conexiones hacia la red de la oficina. Los usuarios acceden por HTTPS desde el navegador.

## Artefactos de una release

Crear una misma versión para los dos servicios:

```bash
VERSION=0.1.0
REGISTRY=registry.example.com/crm
docker build --target production -t "$REGISTRY/backend:$VERSION" backend
docker build --target production -t "$REGISTRY/frontend:$VERSION" frontend
docker push "$REGISTRY/backend:$VERSION"
docker push "$REGISTRY/frontend:$VERSION"
```

Antes de una entrega estable se deben sustituir los tags del archivo de entorno por referencias con digest (`image@sha256:...`). El tag facilita identificar la release y el digest garantiza que el artefacto no cambie.

## Primera instalación

1. Copiar únicamente `compose.production.yaml`, `infrastructure/caddy/Caddyfile`, los scripts operativos y un archivo `.env.production` creado desde `.env.production.example`.
2. Generar secretos distintos mediante un generador criptográfico. Para evitar problemas de URL en `DATABASE_URL`, puede utilizarse `openssl rand -hex 32` para la contraseña de PostgreSQL.
3. Proteger el archivo: `chmod 600 .env.production`.
4. Configurar los tags o digests de las imágenes y apuntar el DNS al servidor.
5. Validar la configuración sin guardar su salida, porque contiene secretos:

   ```bash
   docker compose --env-file .env.production -f compose.production.yaml config --quiet
   ```

6. Descargar y arrancar:

   ```bash
   docker compose --env-file .env.production -f compose.production.yaml pull
   docker compose --env-file .env.production -f compose.production.yaml up -d
   docker compose --env-file .env.production -f compose.production.yaml ps
   ```

El servicio `migrate` ejecuta `alembic upgrade head` antes de que arranque el backend. Si una migración falla, el backend nuevo no comienza a servir tráfico.

7. Ejecutar `infrastructure/production/smoke-test.sh https://crm.example.com`.
8. Completar el asistente de primer inicio y guardar las credenciales del propietario en el gestor de secretos acordado.

En producción `FRONTEND_PUBLIC_URL` debe usar HTTPS, el backend de correo no puede ser `console` y la clave maestra de IA debe tener al menos 32 caracteres. `EMAIL_BACKEND=disabled` permite arrancar sin correo, pero no se podrán enviar invitaciones. Para habilitarlas se configura SMTP y se cambia a `EMAIL_BACKEND=smtp`.

## Backups y restauración

Crear un backup lógico:

```bash
infrastructure/production/backup.sh .env.production /srv/crm/backups
```

El script genera un archivo custom de `pg_dump`, valida que `pg_restore` pueda leerlo, calcula SHA-256 y restringe sus permisos. El directorio local no constituye por sí solo un backup: cada archivo y su checksum deben copiarse cifrados a otro proveedor o ubicación con una política de retención definida.

Comprobar la restauración sin sobrescribir la base activa:

```bash
infrastructure/production/restore-check.sh .env.production /srv/crm/backups/crm-TIMESTAMP.dump
```

La comprobación crea una base temporal con un nombre controlado, restaura el contenido, consulta la revisión de Alembic y elimina la base temporal al terminar. Debe ejecutarse inicialmente en la instalación piloto y periódicamente. Una restauración de desastre exige detener frontend y backend, conservar un backup de seguridad, restaurar en una base vacía y ejecutar los smoke tests antes de reabrir el acceso.

## Actualización y rollback

1. Revisar migraciones y notas de la release.
2. Crear y replicar un backup verificado.
3. Cambiar `CRM_FRONTEND_IMAGE` y `CRM_BACKEND_IMAGE` al nuevo tag o digest.
4. Ejecutar `pull` y `up -d`; las migraciones se aplican antes del backend.
5. Ejecutar smoke tests y revisar `docker compose ... ps` y logs.

Volver a imágenes anteriores solo es seguro si las migraciones son compatibles hacia atrás. Si no lo son, el rollback requiere restaurar el backup anterior. Nunca se debe ejecutar un downgrade destructivo sobre datos de producción sin un procedimiento específico de esa release.

## Antes de publicar la primera empresa

- decidir quién atiende certificados, backups, alertas y actualizaciones;
- fijar región, encargado del tratamiento y retención;
- elegir SMTP y probar una invitación real;
- elegir la barrera de acceso adicional, como MFA/SSO o un proxy de identidad;
- restringir SSH y revisar el firewall;
- ejecutar la suite completa y una revisión de seguridad;
- verificar una restauración y documentar el resultado;
- validar el comportamiento visual y funcional de owner, admin y employee.

Hasta completar estos puntos los archivos constituyen una preparación reproducible, no una autorización para exponer datos reales.
