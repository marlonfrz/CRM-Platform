# Plan del MVP

## 1. Criterios del plan

Este plan divide el trabajo en incrementos pequeños, verificables y funcionales. El orden prioriza primero integridad del modelo, autenticación y autorización porque todas las funciones posteriores dependen de ellas.

Cada fase debe terminar con:

- migraciones reproducibles cuando existan cambios de datos;
- tests automáticos de reglas críticas;
- documentación actualizada;
- ejecución local mediante Docker Compose desde que la infraestructura esté disponible;
- un incremento demostrable, no una colección de capas incompletas.

No se implementarán funcionalidades fuera de [CRM_CONTEXT.md](../CRM_CONTEXT.md).

## 2. Definición de terminado del MVP

El MVP está terminado cuando una instalación independiente permite:

1. iniciar sesión de forma segura;
2. administrar una organización, usuarios y departamentos según permisos;
3. crear clientes globales;
4. asignarlos a empleados dentro del alcance autorizado;
5. registrar actividades con departamento resuelto por backend;
6. crear y completar tareas;
7. consultar un historial autorizado del cliente;
8. consultar dashboards mínimos por rol;
9. auditar las operaciones críticas;
10. generar resúmenes de IA únicamente con datos autorizados y separados por departamento;
11. desplegar y restaurar la instalación con procedimientos documentados.

## 3. Fases

### Fase 0 — Cierre de decisiones críticas

Objetivo: resolver ambigüedades que pueden cambiar el modelo o los permisos.

Tareas:

- validar las cuestiones abiertas de `ARCHITECTURE.md`;
- documentar como cerradas la visibilidad departamental, la pertenencia múltiple, la edición auditada de actividades y las tareas sin fecha;
- incluir el modo individual sin departamentos ni jerarquía;
- incluir contactos múltiples por cliente;
- fijar el bootstrap mediante comando administrativo y Docker Compose como base de despliegue;
- documentar la caducidad deslizante de sesión de 8 horas y dejar pendientes solo la operación de la primera instalación y la selección posterior de IA;
- convertir la matriz de autorización en criterios de aceptación.

Entregable: arquitectura actualizada y matriz de permisos aprobada. Esta fase queda funcionalmente cerrada con las decisiones del 17/08/2026, salvo decisiones operativas que tienen un punto de cierre explícito antes de su implementación.

No se escribe código de producto.

### Fase 1 — Esqueleto del monorepo y entorno local

Objetivo: obtener una base mínima ejecutable y reproducible.

Tareas:

- crear aplicaciones vacías Next.js y FastAPI;
- configurar PostgreSQL;
- añadir Dockerfiles de desarrollo;
- crear `compose.yaml`;
- configurar variables con `.env.example`;
- añadir linting, typing y tests mínimos;
- crear endpoints de health check;
- configurar CI para validaciones básicas.

Criterios de aceptación:

- un comando levanta frontend, backend y PostgreSQL;
- FastAPI conecta con PostgreSQL;
- frontend alcanza el health check;
- lint, tipos y tests pasan;
- no hay secretos en Git.

Dependencias: Fase 0 para decisiones de herramientas que afecten la estructura.

### Fase 2 — Modelo de datos fundamental

Estado: completada el 17/08/2026 en `codex/phase-2-data-model`.

Objetivo: representar organización, usuarios y departamentos con integridad en base de datos.

Tareas:

- configurar SQLAlchemy y Alembic;
- crear `Organization`, `User`, `Department` y `DepartmentMember`;
- añadir `Organization.mode` y sus invariantes para `INDIVIDUAL` y `BUSINESS`;
- definir `UserStatus` como `PENDING`, `ACTIVE` y `DISABLED` para preparar invitaciones sin implementar todavía el correo;
- definir UUID, timestamps y enums;
- implementar restricciones de organización y unicidad;
- crear el mecanismo de bootstrap del primer owner;
- preparar factories de tests;
- probar migración hacia delante y base vacía.

Criterios de aceptación:

- una instalación nueva crea su esquema mediante migraciones;
- se puede inicializar una organización con owner;
- una organización individual funciona con un único owner y sin departamentos;
- no pueden relacionarse usuarios y departamentos de organizaciones distintas;
- email y nombre departamental cumplen sus restricciones;
- los tests ejecutan sobre PostgreSQL, no sobre un sustituto con semántica diferente.

### Fase 3 — Autenticación

Estado: completada el 19/08/2026 en `codex/phase-3-authentication`.

Objetivo: establecer identidad segura antes de exponer recursos.

Tareas:

- hash de contraseña con Argon2id;
- login y logout;
- sesiones opacas persistidas;
- cookie segura y protección CSRF;
- dependencia FastAPI de usuario autenticado;
- expiración y revocación;
- renovación de `last_used_at`, la expiración y la cookie en cada acceso válido, con expiración tras 8 horas de inactividad;
- desactivación de usuario y revocación de sus sesiones;
- cambio de contraseña con revocación de todas las sesiones;
- auditoría mínima de eventos de autenticación relevantes.

Criterios de aceptación:

- credenciales válidas crean una sesión;
- tokens originales no se guardan en base de datos;
- logout, desactivación y cambio de contraseña invalidan las sesiones correspondientes;
- una sesión sin actividad válida durante 8 horas exige un nuevo login;
- una petición mutante sin protección CSRF se rechaza;
- endpoints protegidos no confían en datos de identidad enviados por el frontend.

### Fase 4 — Motor de autorización

Estado: completada el 19/08/2026 en `codex/phase-4-authorization`.

Objetivo: centralizar roles, alcance departamental y decisiones de acceso.

Tareas:

- implementar políticas puras y contexto de autorización;
- cubrir `OWNER`, `ADMIN` y `EMPLOYEE`;
- cubrir el bypass explícito del único owner en modo individual, sin departamentos ni asignaciones ficticias;
- implementar alcance de admin mediante `DepartmentMember`;
- crear matriz de tests permitidos/denegados;
- integrar políticas en casos de uso de organización, usuarios y departamentos;
- verificar que listados y detalle usan el mismo alcance.

Criterios de aceptación:

- owner opera sobre toda su organización;
- admin no administra otro departamento;
- employee no accede a administración;
- admin ve el catálogo global de clientes, pero no actividad ajena a sus departamentos;
- el owner individual accede a sus recursos sin relaciones departamentales;
- ningún endpoint usa el frontend como autoridad;
- no existen condicionales de rol dispersos en las rutas;
- las pruebas incluyen intentos de acceso cruzado.

### Fase 5 — Administración mínima de organización

Estado: completada el 19/08/2026 en `codex/phase-5-administration`. Incluye acceso visual, setup, organización, departamentos, usuarios, membresías e invitaciones de un solo uso.

Objetivo: permitir que el owner configure la empresa y que cada rol vea lo que corresponde.

Tareas:

- consultar y actualizar los datos mínimos de organización;
- CRUD mínimo de departamentos;
- crear, listar, editar, activar y desactivar usuarios;
- asignar membresías departamentales;
- aplicar políticas y auditoría;
- construir las pantallas administrativas mínimas.

Criterios de aceptación:

- owner configura departamentos y usuarios;
- admin solo consulta/gestiona lo aprobado en su alcance;
- no se puede dejar una organización sin owner activo;
- cambios críticos producen eventos de auditoría;
- la interfaz representa denegaciones sin sustituir la validación backend.

### Fase 6 — Clientes globales

Estado: completada el 03/09/2026 en `codex/phase-6-global-clients`. Incluye clientes globales, búsqueda por nombre, ficha editable, contactos múltiples, autorización por organización y auditoría. El acceso operativo del empleado se habilita con las asignaciones de la fase 7.

Objetivo: gestionar una ficha de cliente sencilla y sus personas de contacto sin ligarlos a un departamento.

Tareas:

- crear modelo y migración `Client`;
- crear modelo y migración `ClientContact` con datos básicos;
- casos de uso de creación, consulta y actualización;
- listado y búsqueda mínima por nombre;
- políticas de acceso todavía sin asignaciones de empleado;
- pantallas de lista, creación y ficha básica;
- alta, edición y eliminación auditada de personas de contacto;
- auditoría de altas y cambios.

Criterios de aceptación:

- un cliente tiene `organization_id` y nunca `department_id`;
- un cliente puede tener varias personas de contacto sin duplicar su ficha;
- no existen copias por departamento;
- un usuario no puede consultar clientes de otra organización;
- un admin puede ver y crear clientes globales y gestionar sus contactos;
- un employee solo accede a clientes asignados y sus contactos;
- la ficha solo contiene los campos justificados por el contexto.

### Fase 7 — Asignación de clientes

Estado: implementada el 07/09/2026 en `codex/phase-7-client-assignments`. Incluye migración, API de asignación y retirada, equipo asignado en la ficha y vista «Mis clientes» de solo lectura. Verificación automatizada: 62 pruebas de backend y 14 de frontend superadas; migración aplicada y comprobada en Docker. Pendiente la comprobación visual con una sesión autenticada.

Objetivo: convertir las asignaciones en la base del acceso operativo del empleado.

Tareas:

- crear `ClientAssignment`;
- implementar asignar y desasignar;
- validar alcance del asignador y membresía del empleado;
- endpoint y pantalla `Mis clientes`;
- omitir asignaciones en modo individual, donde el owner accede directamente a todos sus clientes;
- auditar asignaciones;
- añadir tests de consultas filtradas.

Criterios de aceptación:

- owner puede asignar según la matriz aprobada;
- admin solo asigna a empleados bajo su alcance;
- admin puede elegir cualquier cliente global para asignarlo dentro de su alcance;
- employee solo lista clientes asignados;
- asignar no duplica clientes;
- las operaciones y eventos de auditoría son atómicos.

Comprobación funcional manual:

1. En modo empresa, crear y activar un empleado con al menos un departamento.
2. Como owner, abrir una ficha de cliente y asignarlo desde «Equipo asignado».
3. Como empleado, comprobar que «Mis clientes» permite buscar y consultar únicamente sus clientes asignados y contactos, sin edición.
4. Como admin, comprobar que puede usar cualquier cliente global, pero solo ve y gestiona asignaciones de empleados con al menos un departamento compartido.
5. Retirar una asignación y comprobar que la siguiente consulta del empleado ya no permite acceder al cliente; la ficha y sus contactos permanecen.
6. En modo individual, comprobar que el owner sigue gestionando sus clientes sin controles ni solicitudes de asignación.

### Fase 8 — Actividades

Estado: implementada el 07/09/2026. Incluye modelo y migración, registro y corrección auditados, filtros y paginación, permisos por rol/departamento/asignación y componentes de ficha para empresa y uso individual. Validación automatizada: 86 pruebas backend y 22 frontend superadas, lint, tipos y build correctos. Pendiente la revisión visual con sesión autenticada.

Objetivo: entregar el núcleo de valor: registrar lo que ocurrió con un cliente.

Tareas:

- crear `Activity` y tipos fijos;
- implementar resolución del departamento;
- formulario rápido de actividad;
- registrar `occurred_at`, descripción y próxima acción opcional;
- listar actividades con filtros autorizados mínimos;
- auditar creación y las correcciones que se aprueben;
- probar cambio posterior de membresía sin alterar la atribución histórica.

Criterios de aceptación:

- employee registra actividad solo en un cliente accesible;
- el backend asigna o valida el departamento;
- en modo individual el backend registra la actividad sin departamento;
- una actividad conserva usuario y departamento históricos;
- admin solo ve actividad dentro del alcance aprobado;
- owner ve toda la actividad;
- no se pide departamento cuando solo hay una opción válida.

Comprobación funcional manual:

1. Abrir un cliente y pulsar «Nueva actividad». Registrar tipo, descripción, fecha opcional y próxima acción opcional. La fecha vacía usa la hora actual; las fechas explícitas se introducen en UTC.
2. Con una membresía, comprobar la atribución automática. Con varias, elegir un departamento permitido. En modo individual, comprobar la ausencia de controles departamentales.
3. Como admin, comprobar que el listado y sus filtros no muestran actividad de otros departamentos; como empleado, además exigir asignación al cliente. El owner empresarial consulta toda la actividad.
4. Corregir una actividad reciente sin cambiar su autor ni departamento. Comprobar que después de 24 horas desde su registro no se puede corregir, tampoco como owner.
5. Cambiar una membresía y comprobar que la actividad conserva su departamento histórico. Retirar una asignación y comprobar que el empleado pierde acceso en la siguiente consulta.
6. Intentar eliminar un departamento con actividad y comprobar el mensaje de conservación del historial.

No incluye tareas, envío de emails, IA ni el historial unificado de fases posteriores.

### Fase 9 — Tareas

Estado: implementada el 07/09/2026. Incluye migración, API, tareas en ficha, «Mis tareas», responsable autorizado, fecha opcional, edición de pendientes, finalización idempotente y auditoría transaccional. Suite completa: 118 pruebas backend y 29 frontend superadas; lint, tipos y build correctos.

Migración aplicada y verificada en Docker. Comprobación en navegador con admin de pruebas: acceso a «Mis tareas», apertura del formulario en ficha, responsables disponibles, campos opcionales y maquetación en viewport estrecho. Se canceló el formulario sin guardar datos y se cerró la sesión. Los flujos de escritura y demás roles están cubiertos por las pruebas automatizadas, no por un recorrido visual completo.

Objetivo: representar trabajo pendiente sin mezclarlo con actividad histórica.

Tareas:

- crear `Task`;
- crear, listar, actualizar y completar;
- vistas `Mis tareas` y tareas del cliente;
- validar responsable y acceso al cliente;
- auditar creación, reasignación y finalización;
- cubrir estados `PENDING` y `COMPLETED`.

Criterios de aceptación:

- las tareas no se almacenan como actividades;
- un responsable solo puede asignarse si tiene acceso válido al cliente;
- employees gestionan sus tareas según la matriz;
- no se añaden prioridad, recurrencia ni estados configurables.
- `due_at` puede ser nulo para tareas abiertas o acciones futuras sin fecha.

Comprobación funcional:

1. En la ficha del cliente, crear una tarea con y sin fecha límite. En empresa, elegir departamento solo cuando haya varias opciones; en individual no se elige departamento ni responsable.
2. Como admin, elegir un empleado activo del departamento que tenga asignado el cliente. Como empleado, crear una tarea propia y comprobar que no se puede asignar a otra persona.
3. Consultar «Mis tareas», filtrar por estado y abrir la ficha desde el enlace del cliente. Esta vista solo contiene responsabilidades propias; la ficha ofrece las tareas del alcance autorizado.
4. Editar una tarea pendiente, cambiar o quitar su fecha y reasignarla como owner/admin. Verificar que desaparece de «Mis tareas» del responsable anterior y aparece al nuevo responsable.
5. Completar con confirmación y comprobar la fecha de finalización, ausencia de edición posterior y un único evento de auditoría ante repetición.
6. Retirar la asignación o membresía de un empleado y comprobar que pierde acceso sin destruir la tarea; el owner/admin de su departamento puede reasignarla para recuperar el trabajo.

No incluye prioridades, recurrencia, recordatorios, calendario, reapertura, borrado ni conversión automática de actividades en tareas. La fase 10 no se inicia con esta entrega.

### Fase 10 — Historial del cliente y dashboards mínimos

Estado: implementada el 09/09/2026. Incluye historial autorizado con filtro y paginación, dashboard por rol y modo individual, métricas SQL y componentes reutilizables con CSS Modules. Suite completa: 131 pruebas backend y 38 frontend superadas. No requiere nuevas migraciones ni dependencias. El commit previo a esta fase es `e55a3ea`.

Validación de cierre: lint y tipos de ambos servicios, build de frontend y `git diff --check` correctos. Docker Compose reconstruido con servicios saludables y `alembic check` sin cambios de esquema. Revisión visual en navegador: dashboard de admin y empleado, historial de un cliente existente y filtro «Solo tareas» con estado vacío; sesiones cerradas al terminar, sin modificar datos de negocio. Owner, modo individual, tareas con contenido y paginación múltiple quedan verificados mediante pruebas automatizadas, no mediante un recorrido visual completo. El formato de los nueve archivos Python de la fase pasa; la comprobación global conserva dos avisos previos en `app/schemas/clients.py` y `tests/test_clients.py`, ajenos a esta fase.

Objetivo: convertir actividades y tareas existentes en vistas útiles por rol.

Tareas:

- consulta autorizada y paginada del historial;
- presentación cronológica de actividades y tareas;
- dashboard employee: mis clientes, mis tareas y actividad reciente;
- dashboard admin: departamento, empleados, clientes, tareas y actividad;
- dashboard owner: organización, departamentos, actividad, clientes y usuarios;
- pruebas de fuga de información en agregaciones y listados.

Criterios de aceptación:

- cada rol recibe únicamente datos autorizados;
- el historial identifica quién, departamento, qué y cuándo;
- no existe constructor de dashboards;
- no se crea una tabla genérica de timeline sin necesidad.

Comprobación funcional:

1. Abrir Inicio como owner, admin y empleado y contrastar las métricas con los listados permitidos. El admin ve el catálogo global de clientes, no actividad o tareas de otros departamentos.
2. Abrir la ficha de un cliente y consultar «Historial del cliente»: combinar actividades y tareas, filtrar cada tipo y navegar páginas sin perder los filtros de las otras secciones.
3. Comprobar que cada actividad identifica autor y fecha; cada tarea identifica responsable, estado actual y fecha de finalización o creación. No se presentan versiones históricas ni se afirma quién completó una tarea a partir de su responsable.
4. Retirar una asignación o membresía y verificar que los nuevos accesos ya no incluyen registros fuera de alcance, tampoco en los contadores.
5. En modo individual, comprobar Inicio e historial sin departamentos, equipos ni asignaciones.
6. Comprobar estados vacíos, los cinco elementos máximos de cada resumen y las tareas sin fecha al final.

Estos casos están cubiertos por pruebas automatizadas. La fase 11 y su consulta de auditoría quedan fuera de esta entrega.

### Fase 11 — Auditoría operativa

Estado: implementada el 09/09/2026. Consulta exclusiva de owner empresarial e individual, filtros, paginación, índice, catálogo de metadatos validado y cobertura adicional de bootstrap, reenvío y membresías. Conservación sin purga automática. Contrato y limitaciones en [AUDIT.md](../AUDIT.md). No se inicia la fase 12.

Validación: 151 pruebas backend y 46 frontend superadas; lint, tipos y build correctos. Migración `20260909_0008` aplicada en Docker y `alembic check` sin divergencias. La vista owner está verificada mediante pruebas de renderizado y API; queda pendiente su recorrido visual con una sesión owner, cuya contraseña no se ha modificado ni restablecido.

Objetivo: completar una trazabilidad básica, consultable y segura.

La tabla y los primeros eventos ya existen desde fases tempranas; esta fase cierra cobertura y consulta.

Tareas:

- revisar catálogo mínimo de eventos;
- garantizar escritura transaccional;
- añadir consulta de auditoría para owner;
- definir retención y paginación;
- comprobar exclusión de secretos y contenido sensible innecesario;
- probar inmutabilidad desde la API.

Criterios de aceptación:

- las acciones críticas responden quién, qué, sobre qué y cuándo;
- usuarios normales no modifican ni eliminan auditoría;
- el fallo de auditoría revierte operaciones cubiertas;
- metadata tiene límites y contrato explícito.

### Fase 12 — Resúmenes de IA

Objetivo: aportar resúmenes útiles sin delegar permisos ni estructura al LLM.

Condición de entrada: permisos, historial y auditoría están completos y probados.

Tareas:

- decidir proveedor y requisitos de privacidad;
- comparar al menos una alternativa gratuita y alternativas de pago por calidad, límites, privacidad y coste;
- definir interfaz de adaptador LLM;
- crear selector autorizado de actividades;
- agrupar contexto por departamento;
- minimizar y registrar los datos enviados;
- resumen de cliente para owner/admin según alcance;
- resumen departamental;
- informe global para owner;
- resumen único sin agrupación departamental en modo individual;
- validación de salida, errores y límites;
- pruebas con proveedor simulado.

Criterios de aceptación:

- el proveedor nunca recibe información no autorizada;
- el backend proporciona el departamento explícitamente;
- un admin no obtiene datos de otro departamento;
- la aplicación funciona sin IA si el proveedor no está configurado;
- el núcleo no queda acoplado a un proveedor ni a un único nivel gratuito/de pago;
- no se incorpora una cola hasta demostrar su necesidad.

### Fase 13 — Endurecimiento y entrega de una instalación

Objetivo: desplegar de forma repetible una primera instalación independiente.

Tareas:

- imágenes de producción;
- `compose.production.yaml`;
- reverse proxy y HTTPS;
- secretos de instalación;
- PostgreSQL no expuesto;
- procedimiento de migración;
- backups y restauración probada;
- smoke tests;
- logs y health checks;
- documentación de actualización y rollback;
- revisión de seguridad y permisos completa.

Criterios de aceptación:

- el cliente recibe artefactos, no el repositorio;
- la instalación arranca desde imágenes versionadas;
- una restauración de backup se demuestra;
- despliegue y actualización están documentados;
- ninguna base de datos o endpoint interno queda expuesto por defecto.

## 4. Estrategia de pruebas por nivel

### Unitarias

- políticas de autorización;
- resolución del departamento;
- validaciones de casos de uso;
- preparación y agrupación de contexto para IA.

### Integración

- repositorios y restricciones PostgreSQL;
- migraciones;
- autenticación y sesiones;
- transacciones con auditoría;
- consultas con alcance.

### API

- contratos y errores;
- autenticación/CSRF;
- respuestas 401/403/404 sin filtrar existencia indebida;
- paginación y filtros permitidos.

### End-to-end

Un flujo crítico por rol:

- owner crea departamento, admin y employee;
- admin asigna un cliente a employee;
- employee registra actividad y completa una tarea;
- admin consulta su departamento;
- owner consulta visión global;
- un usuario intenta y no consigue acceder fuera de alcance.

### Seguridad

- aislamiento entre organizaciones en fixtures;
- IDOR en todos los recursos;
- escalada de privilegios por IDs enviados;
- sesiones revocadas;
- entrada maliciosa y límites;
- ausencia de secretos en logs y respuestas.

## 5. Dependencias entre fases

```text
Decisiones
   ↓
Entorno
   ↓
Modelo de datos
   ↓
Autenticación
   ↓
Autorización
   ↓
Administración
   ↓
Clientes
   ↓
Asignaciones
   ↓
Actividades ──→ Historial y dashboards
   ↓                    ↓
Tareas ────────────────┘
                        ↓
                  Auditoría cerrada
                        ↓
                       IA
                        ↓
              Entrega de instalación
```

La auditoría comienza en autenticación y acompaña cada fase; su fase propia revisa cobertura. La seguridad y los tests no son una fase final: forman parte de cada incremento.

## 6. Elementos explícitamente aplazados

- modo SaaS multi-tenant compartido;
- licencias firmadas e `installation_id`;
- empaquetado especial del backend;
- MFA y SSO;
- Redis, colas y workers;
- Kubernetes;
- múltiples emails o teléfonos por una misma persona de contacto, salvo necesidad demostrada;
- custom fields;
- pipelines;
- facturación y presupuestos;
- proyectos, calendario, email y documentos;
- automatizaciones;
- integraciones externas;
- dashboards configurables;
- tipos y estados completamente configurables;
- IA avanzada distinta de los resúmenes definidos.

Aplazar significa no diseñar tablas o abstracciones especulativas para estas funciones. Se conservarán límites modulares y migraciones limpias para poder añadirlas cuando exista una necesidad real.

## 7. Riesgos principales y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Fuga de actividad entre departamentos | Matriz cerrada, políticas centralizadas y tests negativos |
| Relaciones cruzadas de organización | `organization_id`, FKs/restricciones compuestas y tests de integración |
| Departamento ambiguo en una actividad | Resolver membresías en backend y exigir elección solo si hay varias válidas |
| Scope creep | Criterios de fase y lista explícita de aplazados |
| Auditoría incompleta | Escritura transaccional desde fases tempranas |
| Datos privados enviados a IA | Selección autorizada, minimización, adaptador y decisión de proveedor previa |
| Complejidad operativa | Docker Compose y PostgreSQL; sin servicios no justificados |
| Variantes por cliente | Código base único, configuración mínima y artefactos versionados |
| Pérdida de datos | Backups y restauración probada antes de entregar |
| Protección del código sobreestimada | Repositorio privado y artefactos, asumiendo límites del control del servidor |

## 8. Primer hito recomendado

El primer hito de implementación debe abarcar únicamente las fases 0 a 4:

- decisiones críticas;
- entorno reproducible;
- modelo fundamental;
- autenticación;
- motor de autorización.

Resultado: una base ejecutable donde un usuario puede autenticarse y las reglas `Owner / Admin por departamento / Employee` están demostradas mediante tests, antes de introducir clientes o actividad.
