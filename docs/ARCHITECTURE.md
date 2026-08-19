# Arquitectura del CRM

## 1. Propósito y límites

Este documento traduce [CRM_CONTEXT.md](./CRM_CONTEXT.md) a una arquitectura inicial. El producto es una aplicación privada para gestionar clientes y la actividad de una organización. No es un SaaS multi-tenant compartido ni un CRM comercial genérico.

Cada cliente tendrá una instalación independiente, una base de datos independiente y sus propios secretos. El repositorio y el núcleo del producto serán únicos para evitar variantes por cliente.

El MVP incluye:

- autenticación;
- organización en modo individual o empresa, con usuarios y departamentos cuando correspondan;
- roles y autorización por alcance;
- clientes globales dentro de la organización y sus personas de contacto;
- asignación de clientes a usuarios;
- actividades asociadas a usuario y departamento;
- tareas;
- historial del cliente;
- auditoría básica;
- resúmenes de IA posteriores al núcleo funcional.

Quedan fuera del MVP las funcionalidades enumeradas expresamente en `CRM_CONTEXT.md`, incluidas facturación, presupuestos, ERP, campañas, pipelines configurables, custom fields universales, workflows, chat, gestión documental avanzada y SaaS multi-tenant.

## 2. Decisiones de producto cerradas

- Existe un único código base reutilizable.
- Cada cliente usa una instalación y una base de datos independientes.
- La aplicación modela una organización incluso en instalaciones de uso individual.
- El modo individual y el modo empresa comparten núcleo y modelo: el individual tiene un único `OWNER` y no muestra ni exige departamentos, jerarquía, usuarios o asignaciones.
- El MVP desarrolla primero las reglas del modo empresa por ser el caso más restrictivo, pero cada fase funcional debe comprobar también el flujo individual.
- Los roles base son `OWNER`, `ADMIN` y `EMPLOYEE`.
- Un `ADMIN` solo administra los departamentos en los que tiene alcance.
- Un cliente pertenece a la organización, no a un departamento.
- Un `ADMIN` puede consultar el catálogo completo de clientes y sus contactos, crear clientes y vincular clientes existentes al trabajo de sus departamentos, sin depender del owner.
- Un cliente puede tener varias personas de contacto con sus datos básicos de comunicación.
- Un usuario puede pertenecer a varios departamentos.
- Los usuarios pueden ser asignados a clientes sin duplicar esos clientes.
- Una actividad pertenece al cliente, al autor y al departamento desde el que se realizó.
- El departamento de la actividad lo determina el backend.
- En modo individual, una actividad no necesita departamento porque no existe contexto departamental.
- Actividades y tareas son conceptos diferentes.
- Las tareas pueden quedar abiertas sin fecha límite.
- Al desactivar un usuario o cambiar su contraseña se revocan todas sus sesiones.
- El backend es la autoridad de permisos.
- La IA solo recibe datos previamente autorizados y agrupados por el backend.
- La auditoría se incorpora desde una fase temprana.

## 3. Decisiones técnicas y alternativas

### 3.1 Repositorio

Opciones:

1. Repositorios separados para frontend, backend e infraestructura.
2. Monorepo con aplicaciones separadas.

Elección: monorepo.

Es la alternativa más sencilla para coordinar contratos API, Docker Compose, documentación y versiones de una instalación. Frontend y backend conservan límites independientes y podrán construirse como imágenes distintas.

Estructura objetivo:

```text
crm-platform/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── features/
│   │   ├── components/
│   │   └── lib/
│   └── tests/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── auth/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── policies/
│   │   ├── repositories/
│   │   ├── schemas/
│   │   └── services/
│   ├── migrations/
│   └── tests/
├── infrastructure/
│   ├── proxy/
│   └── scripts/
├── docs/
│   ├── CRM_CONTEXT.md
│   ├── ARCHITECTURE.md
│   └── plans/
│       └── MVP_PLAN.md
├── compose.yaml
├── compose.production.yaml
└── .env.example
```

Las carpetas de implementación se crearán cuando comience la fase correspondiente; esta tarea solo crea documentación.

### 3.2 Frontend

Elección: Next.js con TypeScript y App Router.

El frontend se ocupa de la interfaz, navegación, formularios y presentación de datos. No decide autorizaciones. Puede ocultar acciones por experiencia de usuario, pero toda operación vuelve a validarse en FastAPI.

Organización propuesta:

- `app/`: rutas y layouts;
- `features/`: módulos de organización, usuarios, clientes, actividades y tareas;
- `components/`: componentes visuales compartidos;
- `lib/api/`: cliente HTTP y contratos generados o tipados;
- `lib/auth/`: estado de sesión y guardas de navegación, sin reglas de autorización definitivas.

No se decide todavía una librería visual concreta porque el contexto no la requiere. Se elegirá al iniciar el frontend comparando mantenimiento, accesibilidad y coste de personalización.

### 3.3 Backend

Elección: FastAPI, Python, SQLAlchemy 2, Alembic y Pydantic.

Alternativas consideradas:

- arquitectura de microservicios;
- monolito modular.

Se elige un monolito modular. El dominio es pequeño, una instalación pertenece a un cliente y no existe una necesidad demostrada de despliegue o escalado independiente. Los módulos internos y las políticas centralizadas mantienen una vía de crecimiento sin coste operativo innecesario.

Responsabilidades:

- `api/`: transporte HTTP, dependencias y serialización;
- `services/`: casos de uso y transacciones;
- `policies/`: decisiones de autorización;
- `repositories/`: consultas reutilizables cuando aporten claridad;
- `models/`: persistencia;
- `schemas/`: entrada y salida;
- `auth/`: sesión, contraseñas y principal autenticado;
- `core/`: configuración, errores y utilidades transversales.

Las rutas no contendrán reglas de negocio complejas ni condicionales de rol dispersos.

### 3.4 Base de datos

Elección: PostgreSQL.

Aunque cada instalación solo aloje inicialmente una organización, las entidades de negocio conservarán `organization_id`. Esto:

- representa correctamente el dominio;
- evita asociaciones accidentales entre organizaciones;
- facilita pruebas de aislamiento;
- permite el modo individual sin otro modelo;
- no convierte la solución en un SaaS compartido.

Las claves foráneas y restricciones compuestas deben impedir relaciones cruzadas. El aislamiento principal sigue siendo una base de datos por cliente.

### 3.5 Autenticación

Opciones:

1. JWT de acceso y refresh almacenados por el navegador.
2. Sesión opaca persistida en PostgreSQL y cookie segura.

Elección para el MVP: sesión opaca con cookie `HttpOnly`, `Secure` en producción y `SameSite=Lax`.

Motivos:

- revocación inmediata;
- cierre de sesiones por usuario;
- menor exposición de credenciales al código del navegador;
- no requiere Redis;
- encaja con una aplicación web privada y un backend central.

La sesión almacenará un hash del token opaco, un hash del token CSRF, usuario, expiración, creación y última utilización. Las contraseñas se almacenarán con Argon2id. Las peticiones mutables tendrán protección CSRF de doble envío: cookie legible por el frontend, cabecera `X-CSRF-Token` y comparación adicional con el hash asociado a la sesión. No se implementará OAuth, SSO o MFA en el MVP, aunque el diseño no debe impedir añadir MFA después.

### 3.6 API

Elección: REST JSON bajo `/api/v1`.

GraphQL no aporta una ventaja demostrada para este alcance. OpenAPI será el contrato verificable entre frontend y backend. Los errores tendrán un formato estable y códigos de dominio; nunca se confiará en mensajes libres para lógica del frontend.

### 3.7 Despliegue

Elección: imágenes Docker y Docker Compose.

Servicios iniciales:

- reverse proxy;
- frontend;
- backend;
- PostgreSQL.

No se añaden Redis, RabbitMQ ni Kubernetes. Los resúmenes de IA pueden ejecutarse síncronamente en el primer corte funcional; si las mediciones demuestran esperas o volumen problemáticos, se diseñará procesamiento en segundo plano en una fase posterior.

La base de datos no publicará puertos en producción. El reverse proxy será el único punto expuesto y terminará HTTPS. Cada instalación tendrá variables, secretos, volúmenes y copias de seguridad propios. Los clientes recibirán artefactos de producción, no el repositorio.

La elección concreta entre Nginx y Traefik queda abierta hasta definir el entorno de despliegue inicial. Nginx es preferible si se busca una configuración estática mínima; Traefik solo se justifica si la automatización de certificados y descubrimiento Docker reduce operación real.

### 3.8 Modos individual y empresa

Opciones consideradas:

1. mantener dos aplicaciones o esquemas diferentes;
2. usar el mismo núcleo con un modo explícito por organización.

Se elige un único núcleo con `Organization.mode = INDIVIDUAL | BUSINESS`.

En modo `INDIVIDUAL`:

- existe un único usuario `OWNER`;
- no se crean departamentos ni membresías;
- no se muestran administración de usuarios, jerarquía ni asignaciones;
- el owner accede directamente a todos sus clientes, contactos, actividades y tareas;
- `Activity.department_id` es nulo porque no existe un departamento real que atribuir.

En modo `BUSINESS` se aplican roles, departamentos, membresías, asignaciones y separación de actividad. No se crearán departamentos ficticios para una persona: simplificarían algunas consultas, pero contaminarían el dominio y la interfaz con conceptos que el usuario individual no necesita.

## 4. Modelo de datos del MVP

Todas las entidades usan UUID, marcas temporales en UTC y claves foráneas explícitas. Los nombres son conceptuales; la migración inicial fijará tipos y nombres definitivos.

### 4.1 Organization

- `id`
- `name`
- `mode`: `INDIVIDUAL | BUSINESS`
- `created_at`
- `updated_at`

Una instalación tendrá una organización activa en el MVP. El modo se establece durante el bootstrap y gobierna las invariantes del caso de uso, no permisos decididos por el frontend.

### 4.2 User

- `id`
- `organization_id`
- `email`
- `full_name`
- `password_hash` opcional mientras el usuario está pendiente
- `role`: `OWNER | ADMIN | EMPLOYEE`
- `status`: `PENDING | ACTIVE | DISABLED`
- `created_at`
- `updated_at`

Restricciones:

- email normalizado único por organización;
- al menos un owner activo debe mantenerse mediante caso de uso transaccional;
- un usuario `PENDING` todavía no ha definido contraseña;
- un usuario `ACTIVE` debe tener `password_hash` y puede autenticarse;
- un usuario `DISABLED` no puede iniciar sesión y conserva su historial;
- el rol no codifica el departamento.

### 4.3 Department

- `id`
- `organization_id`
- `name`
- `created_at`
- `updated_at`

Restricción: nombre normalizado único por organización.

### 4.4 DepartmentMember

- `organization_id`
- `department_id`
- `user_id`
- `created_at`

La pertenencia de un `ADMIN` define su alcance administrativo. La de un `EMPLOYEE` permite atribuir actividades. Un usuario puede pertenecer a varios departamentos; el flujo para crear actividad resuelve una pertenencia inequívoca. En modo individual no existen filas de esta tabla.

Restricciones:

- combinación `department_id + user_id` única;
- usuario y departamento deben pertenecer a la misma organización.

### 4.5 Client

- `id`
- `organization_id`
- `name`
- `address` opcional
- `notes` opcional
- `created_at`
- `updated_at`

No incluye `department_id`. Los datos de personas de contacto se separan para permitir más de una sin duplicar el cliente. No se añaden custom fields ni pipeline en el MVP.

### 4.6 ClientContact

- `id`
- `organization_id`
- `client_id`
- `full_name`
- `position` opcional
- `email` opcional
- `phone` opcional
- `notes` opcional
- `created_at`
- `updated_at`

Cada fila representa una persona de contacto. Un cliente puede tener cero o varias. Para el MVP cada contacto dispone de un email y un teléfono opcionales; solo se añadirá una tabla de métodos de contacto múltiples si aparece una necesidad real.

Restricciones:

- contacto y cliente deben pertenecer a la misma organización;
- debe existir al menos un nombre;
- email y teléfono se validan cuando estén presentes, sin imponer unicidad porque pueden compartirse.

### 4.7 ClientAssignment

- `id`
- `organization_id`
- `client_id`
- `user_id`
- `assigned_by_user_id`
- `created_at`

Restricciones:

- asignación `client_id + user_id` única;
- cliente, usuario y asignador deben pertenecer a la misma organización;
- el servicio debe validar que el asignador puede gestionar al usuario objetivo;
- inicialmente las asignaciones se realizan a empleados, salvo que un requisito posterior justifique otro comportamiento.

No se añade `department_id`: el cliente sigue siendo global y la asignación representa responsabilidad individual. El alcance departamental se obtiene de las membresías del usuario.

En modo individual no se crean asignaciones: el único owner accede directamente a todos los clientes.

### 4.8 Activity

- `id`
- `organization_id`
- `client_id`
- `user_id`
- `department_id` opcional exclusivamente en modo individual
- `type`: `CALL | EMAIL | MEETING | NOTE | INCIDENT | OTHER`
- `description`
- `next_action` opcional
- `occurred_at`
- `created_at`

Restricciones:

- cliente y usuario pertenecen a la misma organización; el departamento también cuando exista;
- el usuario debe estar asignado al cliente o tener permiso administrativo suficiente;
- en modo empresa el usuario debe ser miembro del departamento registrado y `department_id` es obligatorio;
- en modo individual `department_id` debe ser nulo y el usuario debe ser el owner de la organización;
- `department_id` y `user_id` no se aceptan libremente desde un empleado;
- las actividades se tratan como historial: las correcciones futuras deberán ser auditadas.

Se separan `occurred_at` y `created_at` para representar cuándo ocurrió la interacción y cuándo se registró.

Las actividades pueden corregirse durante las primeras 24 horas por su autor, por un admin con alcance sobre el departamento o por el owner. No se eliminan físicamente y toda corrección queda auditada.

### 4.9 Task

- `id`
- `organization_id`
- `client_id`
- `assigned_to_user_id`
- `created_by_user_id`
- `title`
- `description` opcional
- `due_at` opcional
- `status`: `PENDING | COMPLETED`
- `created_at`
- `updated_at`
- `completed_at` opcional

No se incluyen prioridad, recurrencia, calendario ni estados configurables porque no están justificados. El usuario asignado debe tener acceso al cliente.

`due_at` es opcional: una tarea puede representar una acción futura todavía sin fecha.

### 4.10 AuditLog

- `id`
- `organization_id`
- `actor_user_id` opcional para acciones de sistema
- `action`
- `entity_type`
- `entity_id`
- `metadata` JSONB limitado
- `created_at`

Es append-only desde la aplicación. No almacena contraseñas, tokens, descripciones completas ni secretos. Los eventos iniciales cubren autenticación relevante, cambios de usuarios/departamentos, asignaciones, actividades y tareas.

### 4.11 UserSession

- `id`
- `organization_id`
- `user_id`
- `token_hash`
- `expires_at`
- `created_at`
- `last_used_at`
- `revoked_at` opcional

El token original solo viaja en la cookie; la base de datos guarda su hash.

Al desactivar un usuario o cambiar su contraseña, el backend revoca todas sus sesiones en la misma operación transaccional. La sesión tiene una caducidad deslizante de 8 horas: cada acceso autenticado válido actualiza `last_used_at`, `expires_at` y la caducidad de las cookies. El secreto opaco permanece estable durante la sesión para que peticiones simultáneas no se invaliden entre sí; si transcurren 8 horas sin actividad válida, la sesión expira y exige un nuevo login.

## 5. Autorización

La autorización se implementará mediante funciones de política llamadas desde los casos de uso:

```text
authenticated user
    + role
    + department memberships
    + requested resource
    + client assignments
    -> policy decision
```

Políticas mínimas:

- `can_view_client`
- `can_manage_client`
- `can_assign_client`
- `can_create_activity`
- `can_view_activity`
- `can_manage_task`
- `can_manage_department`
- `can_manage_user`
- `can_view_department_report`
- `can_view_global_report`

Reglas base:

| Acción | Owner | Admin | Employee |
|---|---|---|---|
| Ver clientes y contactos | Todos los de la organización | Todos los de la organización | Solo asignados |
| Crear/editar cliente y contactos | Sí | Sí; el cliente sigue siendo global | No inicialmente |
| Asignar cliente | A usuarios de la organización | A empleados de departamentos administrados | No |
| Registrar actividad | En clientes accesibles | En cualquier cliente, atribuida a uno de sus departamentos | En clientes asignados |
| Ver actividad | Toda | Actividad de departamentos administrados | Historial permitido de clientes asignados |
| Gestionar tareas | Toda | Para clientes y usuarios de su alcance | Sus tareas y acciones permitidas |
| Administrar departamentos/usuarios | Toda | Solo alcance departamental permitido | No |
| Informe global | Sí | No | No |
| Informe departamental | Sí | Departamentos administrados | No |

Un admin ve el catálogo completo, la ficha general y los contactos de todos los clientes. Solo ve actividades y tareas de los departamentos que administra. Puede crear un cliente o empezar a trabajar con uno existente desde uno de sus departamentos sin intervención del owner.

Un employee solo ve clientes asignados y, dentro de ellos, actividad perteneciente a departamentos de los que es miembro. El modo individual omite esta matriz: su único owner accede a todos los recursos de la organización.

Las consultas deben aplicar el mismo alcance que las políticas de objetos individuales. No se debe cargar una colección completa y filtrarla en el frontend.

## 6. Asignación de clientes

Flujo de asignación:

1. El backend autentica al actor.
2. Carga cliente, usuario objetivo y sus membresías dentro de la organización.
3. `can_assign_client` comprueba que el actor es owner o administra al menos un departamento del usuario objetivo; el admin puede seleccionar cualquier cliente global de la organización.
4. Se crea la asignación si no existe.
5. Se registra `ASSIGNED_CLIENT` en auditoría dentro de la misma transacción.
6. El empleado puede consultar el cliente mediante esa asignación.

Una asignación no da acceso automáticamente a todos los departamentos ni modifica la propiedad global del cliente.

## 7. Atribución de actividades al departamento

El cliente no envía un `department_id` autoritativo.

Flujo:

1. Se autentica el usuario.
2. Se verifica acceso al cliente.
3. El backend obtiene las membresías departamentales aplicables.
4. En modo individual crea la actividad sin departamento.
5. En modo empresa, si existe una sola membresía aplicable, la selecciona automáticamente.
6. Si existen varias, el usuario elige entre las membresías autorizadas; el backend valida la elección.
7. Se crea la actividad con una instantánea explícita de `user_id` y, cuando corresponde, `department_id`.
8. Se registra `CREATED_ACTIVITY` en la misma transacción.

Guardar `department_id` en la actividad conserva el contexto histórico aunque el usuario cambie de departamento posteriormente.

## 8. Historial del cliente

El historial se construye inicialmente a partir de actividades y tareas, ordenadas por fecha, aplicando autorización en backend. No se introduce una tabla genérica de timeline: añadir esa abstracción ahora duplicaría datos y no está justificado.

El frontend puede presentar una vista unificada, pero cada elemento mantiene su contrato de dominio.

## 9. Flujo conceptual de IA

La IA se implementará después de completar y validar permisos, actividades e historial.

Flujo:

1. El usuario solicita un resumen de cliente o departamento.
2. El backend evalúa la política correspondiente.
3. La consulta recupera exclusivamente actividades autorizadas.
4. El backend agrupa los datos por `department_id`.
5. Se minimiza el contenido enviado: datos necesarios, sin secretos ni campos irrelevantes.
6. Un adaptador de proveedor LLM recibe una estructura explícita.
7. La respuesta se valida y se presenta separada por departamento.
8. Se registra la solicitud en auditoría con metadatos no sensibles.

El LLM no recibe datos antes de la autorización, no decide permisos y no infiere el departamento. En modo individual produce un resumen único sin agrupaciones departamentales artificiales.

La integración se abstraerá mediante un adaptador para poder comparar proveedores antes de elegir. Se prevén posteriormente una modalidad gratuita con límites y una modalidad de pago con el proveedor que ofrezca mejor calidad, pero precios, proveedores y límites no se fijan hasta evaluar resultados al final del núcleo funcional. Retención, consentimiento y modalidad local/externa también deben cerrarse antes de esta fase.

## 10. Transacciones y auditoría

Los cambios de negocio y su evento de auditoría se confirman en una misma transacción. Si falla el registro de auditoría de una acción cubierta, falla la operación completa.

La auditoría de lectura se limitará inicialmente a accesos sensibles que se definan explícitamente; registrar todas las lecturas generaría volumen sin un requisito demostrado.

## 11. Tests

Prioridad de tests:

- restricciones y migraciones del modelo de datos;
- matrices de autorización por rol, departamento y asignación;
- aislamiento por `organization_id`;
- asignación de clientes;
- resolución del departamento de actividad;
- transacciones con auditoría;
- autenticación, revocación y CSRF;
- consultas de historial sin fuga entre departamentos;
- selección de datos previa a la IA;
- flujos críticos end-to-end por cada rol.

Las políticas se probarán como tablas de casos permitidos y denegados. Cada vulnerabilidad de alcance descubierta debe convertirse en un test de regresión.

## 12. Observabilidad, secretos y operación

- configuración mediante variables de entorno validadas;
- secretos fuera de imágenes y repositorio;
- logs estructurados sin contenido privado innecesario;
- identificador de petición para correlación;
- health checks separados de disponibilidad de dependencias cuando corresponda;
- migraciones explícitas antes de arrancar una versión;
- copias de seguridad PostgreSQL y procedimiento de restauración probado;
- HTTPS en accesos públicos;
- PostgreSQL solo en red privada de Docker;
- imágenes versionadas e inmutables.

Licencias, `installation_id`, empaquetado del backend y registry privado son opciones futuras de distribución, no requisitos del MVP funcional.

## 13. Cuestiones abiertas antes de implementar

Las decisiones de producto principales de la Fase 0 están cerradas. Permanecen estas decisiones operativas antes de sus fases correspondientes:

1. Confirmar quién operará backups, certificados y actualizaciones en la primera instalación Docker Compose sobre VPS o servidor del cliente.
2. Para IA: comparar proveedores gratuitos y de pago y decidir residencia/retención de datos, consentimiento, presupuesto y posibilidad de procesamiento local.

Las fases que no dependan de una respuesta pueden comenzar con decisiones conservadoras documentadas. Las preguntas que afectan permisos deben cerrarse antes de exponer el recurso correspondiente.
