# Auditoría operativa — fase 11

## Alcance y acceso

El owner empresarial o individual puede consultar `/audit` en el frontend y `GET /api/v1/audit` en el backend. La política `can_view_audit` exige owner y la misma organización. Admin y employee reciben 403; sin sesión se recibe 401. No se incorporan endpoints de creación, edición ni eliminación de auditoría.

La consulta aplica organización antes de filtros, orden y paginación. La interfaz separa los eventos en «Accesos», «Equipo y permisos», «Clientes», «Actividad», «Organización» e «IA»; cada área limita también las acciones disponibles en el selector detallado. Los filtros opcionales de API son `category`, `action`, `actor_user_id`, `entity_id`, `since` y `until`. Las fechas deben incluir zona horaria y los extremos son inclusivos; el frontend las presenta en UTC. Un rango invertido es inválido. `offset` admite 0–100000 y `limit` 1–100 (20 por defecto). El orden es `created_at DESC, id DESC`; un elemento adicional calcula `has_more`. Una acción desconocida devuelve un listado vacío, sin revelar datos de otra organización.

Se elige offset frente a cursores para mantener el contrato sencillo del MVP. Eventos insertados entre consultas pueden desplazar las páginas: no se promete una instantánea de exportación. El índice `(organization_id, created_at, id)` evita ordenar toda la tabla en las consultas habituales. No se añade Elasticsearch, cola ni servicio de logs externo.

## Catálogo y cobertura

El contrato ejecutable está en `backend/app/schemas/audit.py` (`EVENT_FIELDS`). Todo escritor de la aplicación usa `services/audit.py` dentro de la sesión de la operación.

| Área | Acciones | Datos complementarios |
|---|---|---|
| Primer inicio | `INITIALIZED_ORGANIZATION` | Owner como actor y organización como recurso; sin credenciales |
| Autenticación | `AUTH_LOGIN`, `AUTH_LOGOUT`, `PASSWORD_CHANGED` | UUID de sesión o usuario; nunca token ni hash |
| Organización | `UPDATED_ORGANIZATION` | Nombre anterior y actual |
| Usuarios | `CREATED_USER`, `UPDATED_USER`, `ACTIVATED_USER`, `DISABLED_USER` | Rol y membresías al crear; nombre/rol anteriores y actuales y ambas listas de departamentos al actualizar |
| Invitaciones | `ACCEPTED_INVITATION`, `RESENT_INVITATION` | Usuario afectado; aceptación atribuida al invitado y reenvío al solicitante |
| Departamentos | `CREATED_DEPARTMENT`, `UPDATED_DEPARTMENT`, `DELETED_DEPARTMENT` | Nombres; el evento de eliminación conserva la referencia del departamento retirado |
| Clientes | `CREATED_CLIENT`, `UPDATED_CLIENT` | Nombres; actualización identifica campos cambiados, sin copiar dirección ni notas |
| Contactos | `CREATED_CLIENT_CONTACT`, `UPDATED_CLIENT_CONTACT`, `DELETED_CLIENT_CONTACT` | Cliente y nombre del contacto; actualización identifica campos cambiados, sin copiar email, teléfono ni notas |
| Asignaciones | `ASSIGNED_CLIENT`, `UNASSIGNED_CLIENT` | UUID del cliente y empleado |
| Actividades | `CREATED_ACTIVITY`, `UPDATED_ACTIVITY` | Cliente, autor, departamento y nombres de campos cambiados |
| Tareas | `CREATED_TASK`, `UPDATED_TASK`, `REASSIGNED_TASK`, `COMPLETED_TASK` | Cliente, departamento, responsable y campos cambiados; reasignación incluye responsable anterior |
| IA | `UPDATED_AI_CONFIGURATION`, `AI_SUMMARY_REQUESTED`, `AI_SUMMARY_COMPLETED`, `AI_SUMMARY_FAILED` | Proveedor, modelo, alcance y referencias de origen; nunca token, prompt ni respuesta generada |

Una actualización de usuario cubre el cambio de rol y de membresías en un único evento. La creación inicial de invitación forma parte de `CREATED_USER`. Desactivación y cambio de contraseña incluyen la revocación transaccional de sesiones sin registrar un evento por sesión. La eliminación de departamento implica la retirada de sus membresías; no se duplican eventos por cada miembro. Los helpers internos de construcción de fixtures no son interfaces administrativas públicas.

No se reconstruyen eventos que nunca se registraron en versiones anteriores. `UPDATED_USER` significa que cambiaron datos del perfil, rol o departamentos; no representa una renovación de sesión. No se registran todas las lecturas, refresh tokens, renovaciones de sesión, intentos fallidos anónimos ni expiraciones temporales automáticas. Estos últimos requerirían una política específica de volumen, privacidad y atribución; no se añaden al catálogo operativo en esta fase.

## Contrato de metadatos y privacidad

- Cada acción tiene entidad y claves permitidas. Los campos desconocidos, entidades incompatibles, UUID inválidos o valores fuera del contrato abortan la escritura.
- Máximo 8192 bytes JSON UTF-8 por evento, nombres de hasta 200 caracteres, hasta 20 nombres de campos modificados y hasta 100 UUID por lista de membresías. No se trunca información silenciosamente. Las capacidades que necesiten superar estos límites deberán ampliar el contrato y sus pruebas antes de desplegarse.
- Solo se guardan nombres de campos para los contenidos privados, no sus valores. No se guardan contraseñas, hashes, tokens, enlaces de invitación ni cuerpos de correo.
- Los nombres de autores, clientes, responsables, departamentos, contactos y actividades se resuelven dentro de la organización al consultar. El UUID mantiene la referencia estable en la API, pero la interfaz presenta nombres comprensibles y no expone códigos de acción. Los nombres mostrados son los actuales, no una instantánea histórica; para recursos eliminados se usa el nombre conservado en los metadatos cuando existe. Un actor nulo se presenta como Sistema. Las sesiones conservan su identificador porque no tienen un nombre funcional alternativo.
- La lectura filtra metadatos antiguos por la lista permitida y devuelve `{}` si no puede validarlos. Esto oculta, por ejemplo, emails guardados por versiones anteriores al crear usuarios. No modifica ni purga esos registros originales: los backups y el acceso directo a PostgreSQL siguen siendo sensibles.
- La interfaz presenta metadatos aprobados dentro de detalles desplegables, con etiquetas y valores traducidos: perfiles, alcances, campos modificados y errores se expresan en lenguaje de usuario. El filtro de persona usa nombres aunque internamente envíe el identificador estable. Los textos se escapan y no se ofrece descarga ni exportación masiva.

## Transacciones e inmutabilidad

La misma transacción contiene el cambio de negocio y su auditoría. La dependencia de base de datos confirma al completar el caso de uso y revierte ante excepción. Las pruebas inyectan fallos de inserción de auditoría, además de cubrir los fallos de emisión de actividades, asignaciones y tareas existentes.

Esta garantía es de base de datos. SMTP es un efecto externo y no se puede deshacer si un correo se entrega antes de un fallo posterior del commit. El evento de reenvío indica una operación confirmada cuya llamada SMTP terminó sin error, no garantiza entrega en bandeja de entrada. Resolver la atomicidad entre SMTP y base de datos requeriría outbox/worker y queda fuera de esta fase.

Inmutabilidad significa aquí **sin modificación o eliminación desde la API**. No implica resistencia al administrador del servidor o a SQL directo: las credenciales actuales de PostgreSQL conservan permisos de mantenimiento y no hay firma criptográfica ni almacenamiento WORM. La eliminación completa de una organización mediante mantenimiento SQL puede afectar al registro por la FK existente con cascada.

## Conservación y operación

La decisión conservadora del MVP es **sin borrado automático**. No se introduce un cron de purga ni se elimina ningún evento existente. La auditoría forma parte de los backups de PostgreSQL. El operador debe vigilar el crecimiento y, antes de producción, acordar con el propietario la política de conservación y el tratamiento de copias de seguridad de esa instalación. Un archivo o purga futura deberá ser un procedimiento explícito, con autorización, copia verificable y pruebas; no una acción de la interfaz.

La migración `20260909_0008` añade únicamente el índice, sin reescribir ni eliminar registros. Aplicar con `docker compose exec backend alembic upgrade head` y comprobar con `docker compose exec backend alembic check`. En tablas grandes, la creación convencional de índice puede bloquear escrituras; debe programarse en una ventana de mantenimiento. Su downgrade elimina solo el índice, no los eventos; no ejecutar downgrade en los datos de desarrollo para probarlo, usar la base aislada de tests.

## Verificación

Pruebas específicas: acceso owner/individual, denegación admin/employee/anónimo, aislamiento entre organizaciones incluso en agregados de listado, filtros y fechas, desempate/paginación, privacidad de metadatos antiguos, límites y rechazo de secretos anidados, bootstrap, reenvío, membresías, API de solo lectura y rollback ante fallo de inserción. Frontend: guard de rol antes de consultar, modo individual, estados vacíos, fechas UTC, rangos inválidos, paginación y escape de contenido.

La revisión de seguridad completa y la operación de backups/restauración siguen teniendo su propio cierre en la fase 13; este documento no sustituye esos trabajos.
