# Resúmenes de IA — fase 12

## Estado y alcance

Implementación técnica en `develop`, desactivada por defecto en instalaciones nuevas. El repositorio no contiene binarios de modelos ni credenciales externas. El entorno local de desarrollo puede iniciar Ollama con el perfil opcional `ai`; la instancia de desarrollo actual usa `llama3.2:1b` y datos sintéticos. No se han enviado datos reales a proveedores externos. El owner dispone de `IA > Opciones` para seleccionar proveedor, modelo y token por organización; la elección definitiva y la evaluación comparativa de calidad siguen pendientes.

La pantalla `/summaries` permite resumir actividades de un periodo. Por defecto selecciona desde el inicio del día actual (UTC) hasta el final del mismo día del mes siguiente; el usuario puede cambiar ambas fechas. Incluye trabajo completado en el periodo y actividades pendientes programadas para esos días, diferenciando hechos y planes. La ficha del cliente ofrece un acceso directo a su resumen. No hay chat, búsqueda web, herramientas del modelo, automatizaciones ni modificación de tareas. Los resultados idénticos se reutilizan desde una caché técnica durante 15 minutos por defecto. Además, se conserva el último resumen validado de cada departamento con fecha de generación y periodo cubierto; los resúmenes de un cliente se guardan aparte para no sustituir el resumen departamental general.

| Usuario | Resumen disponible |
|---|---|
| Owner empresarial | Cliente, departamento o toda su organización; secciones separadas por departamento |
| Admin | Cliente limitado a sus departamentos, o un departamento propio |
| Employee | Sin acceso a esta función |
| Owner individual | Cliente o conjunto de sus actividades, sin departamentos artificiales |

El informe global es una colección de resúmenes departamentales, no una segunda consulta que mezcle departamentos. Cada sección actualiza el último resumen de su departamento; el modo individual guarda uno sin departamento. Las próximas acciones provienen de actividades pendientes o del campo `next_action`; no crean ni completan tareas.

## Alternativas y decisión técnica

Comparativa documental consultada el 09/09/2026. La calidad en español, fidelidad a las fuentes y latencia todavía no se han medido en este proyecto.

| Alternativa | Coste y límites | Privacidad y operación | Decisión actual |
|---|---|---|---|
| Ollama con modelo local | Sin tarifa de API por petición; requiere hardware, memoria, electricidad y revisar la licencia del modelo. Rendimiento dependiente del servidor | El operador debe asegurar ejecución local y desactivar capacidades cloud | Adaptador disponible; primera opción a evaluar para uso sin consumo de API |
| OpenAI API | Pago por consumo; precio, cuota y compatibilidad dependen del modelo elegido | Procesamiento externo; el propietario debe revisar las condiciones de datos de su cuenta y proyecto | Adaptador disponible como candidato de pago, no ganador seleccionado |
| Anthropic API | Pago por consumo y límites según modelo | Procesamiento externo; requiere clave de API y revisión de condiciones de datos | Adaptador Claude disponible con salida JSON estructurada |
| Gemini API | Coste y límites según modelo/nivel | Procesamiento externo; requiere una clave restringida a Gemini API | Adaptador disponible con salida JSON estructurada |

Ollama documenta `OLLAMA_NO_CLOUD=1` para desactivar funciones cloud. Debe configurarse en el servidor Ollama, no solo en el CRM. La confirmación local del CRM es una declaración del operador, no una certificación del servidor ni de la licencia del modelo. [FAQ de Ollama](https://docs.ollama.com/faq).

OpenAI se invoca con `store: false`; eso no implica retención cero. Las políticas de monitorización de abuso y sus excepciones deben revisarse antes de autorizar datos de clientes. [Controles de datos de OpenAI](https://developers.openai.com/api/docs/guides/your-data).

Gemini ofrece niveles gratuitos y pagados con distintas condiciones. No se habilita un nivel gratuito externo como alternativa automática para datos privados. Se debe revisar la política aplicable a la cuenta y región antes de comparar usando datos no sintéticos. [Precios y condiciones por nivel de Gemini](https://ai.google.dev/gemini-api/docs/pricing).

Se elige una interfaz Python pequeña con HTTPX, frente a SDKs múltiples, un framework de agentes o una cola: solo se necesita una operación estructurada y acotada. La E/S es asíncrona. Todos los grupos se incluyen en una sola solicitud al proveedor; no se encadenan llamadas por departamento. No hay fallback entre proveedores: un fallo local nunca provoca enviar datos a la nube. La configuración por organización incorpora una tabla y usa AES-GCM mediante `cryptography` para cifrar tokens.

## Datos, permisos y auditoría

1. Validar sesión, CSRF, rol, organización y objetivo.
2. Seleccionar en SQL únicamente actividades autorizadas: completadas por fecha de realización y pendientes por fecha programada dentro del periodo.
3. Separar por departamento y construir un único contexto compacto con todos los grupos.
4. Al pulsar «Generar resumen», calcular un hash con los identificadores reales y consultar la caché vigente para ese contexto, proveedor y modelo.
5. Si no existe caché, confirmar en base de datos `AI_SUMMARY_REQUESTED` antes de invocar el proveedor; si falla este registro no se envía nada.
6. Generar todas las secciones en una sola solicitud y validar grupos, tamaños y referencias.
7. Volver a comprobar sesión y permisos antes de mostrar resultados. Si han cambiado, descartar la respuesta.
8. Guardar temporalmente el resultado completo y, por separado, la última sección validada de cada departamento o cliente; registrar `AI_SUMMARY_COMPLETED` o `AI_SUMMARY_FAILED`.
9. Mostrar junto al resumen un recuadro con los tokens consumidos y el coste orientativo cuando haya datos suficientes; una respuesta desde caché no genera coste nuevo de API.

El proveedor recibe un JSON compacto. `g` contiene los grupos; cada grupo tiene una clave efímera como `g0` y una lista `r`. Cada actividad es un array posicional `[referencia, nombre_cliente, tipo, título, estado, fecha, descripción, próxima_acción]`, donde la referencia es `r0`, `r1`, etc. `COMPLETED` usa fecha de realización UTC y `PENDING` usa el día programado. El prompt aclara que el CRM pertenece al equipo que presta el servicio: el cliente nombrado recibe el trabajo y no debe aparecer como autor salvo que la descripción lo afirme expresamente. Tampoco debe presentar una actividad pendiente como ya realizada. No se envían UUID de departamentos o actividades, fichas de contacto, teléfonos/emails estructurados, datos de usuarios ni notas de la ficha del cliente. El backend conserva el mapa de referencias y reconstruye los UUID después de validar la respuesta. La interfaz muestra título, tipo, descripción, estado y fecha de cada fuente, no su UUID técnico. **Los textos libres pueden contener información personal o instrucciones maliciosas; no hay anonimización automática.** El aviso de interfaz lo explica; la elección de un proveedor externo corresponde al propietario en la configuración de IA, sin casilla por cada resumen.

El modelo recibe los registros como datos no confiables; no dispone de herramientas ni decide los permisos. La interfaz muestra texto escapado, sin interpretar HTML ni enlaces propuestos por el modelo. La validación de citas impide referencias fuera del contexto, pero no demuestra que cada afirmación sea cierta: sigue siendo necesaria revisión humana.

La auditoría conserva actor, fecha, alcance, objetivo, proveedor, modelo, identificadores de actividades, SHA-256 del contexto y si hubo llamada real o reutilización. `UPDATED_AI_CONFIGURATION` registra proveedor y modelo, nunca el token. La auditoría no guarda prompts, respuestas, claves ni errores crudos del proveedor. La caché técnica guarda la respuesta validada hasta su expiración, junto al hash, proveedor y modelo; no guarda el prompt. `ai_summary_latest` guarda solo la última sección por ámbito, con fuentes, fechas y modelo, sin caducidad automática; sustituye la anterior y se elimina al borrar su organización, cliente o departamento. Al leerla se vuelven a comprobar los permisos y se omite cualquier sección con fuentes que ya no sean visibles. Los datos se autorizan al seleccionar la solicitud; una revocación posterior no puede recuperar contenido ya enviado al proveedor. Un corte de proceso o fallo de auditoría final puede dejar solo el evento de solicitud: no demuestra recepción ni finalización del proveedor. No se reintenta automáticamente.

## Contrato y límites

- `GET /api/v1/ai/options`: configuración pública mínima y departamentos autorizados; sin secretos ni conexión al proveedor.
- `GET /api/v1/ai/configuration`: configuración de la organización, solo para owner; devuelve si existe token, nunca su valor.
- `PUT /api/v1/ai/configuration`: guarda proveedor, modelo y, cuando se sustituye, token; solo owner y protegido por CSRF.
- `POST /api/v1/ai/summaries`: `scope`, objetivo `client_id` o `department_id` cuando corresponde, `since` y `until` con zona horaria. No acepta configuración del proveedor desde el navegador. No hay estimación ni confirmación adicional por petición.
- `GET /api/v1/ai/summaries/latest`: `scope` y objetivo opcional, con las últimas secciones visibles para el usuario y sus fechas de generación y cobertura. No llama al proveedor.
- Periodo inclusivo máximo: 366 días. La interfaz etiqueta las fechas como UTC.
- Máximo total de 50 actividades, 8 grupos y 32.000 bytes del JSON compacto UTF-8. Se rechaza el exceso con 413, sin truncar silenciosamente.
- Sin actividades: respuesta vacía y ninguna consulta al modelo.
- Una llamada real al proveedor cada 30 segundos por organización, configurable mediante `AI_COOLDOWN_SECONDS`. Un acierto de caché no consume este intervalo. No es un límite de gasto ni garantiza una sola petición en vuelo si una anterior tarda más.
- Tiempo total de consultas: 45 segundos por defecto en la aplicación, configurable entre 1 y 300 con `AI_TIMEOUT_SECONDS`. Compose usa 180 segundos para admitir modelos locales sin aceleración. La cancelación local no garantiza cancelar trabajo o facturación remotos.
- Respuesta del proveedor limitada a 65.536 bytes; resumen de 2.000 caracteres por sección, hasta 8 próximas acciones de 400 caracteres y referencias válidas, únicas y del mismo grupo.
- El contrato interno solicita como máximo 600 caracteres, 4 próximas acciones de 180 caracteres y claves cortas. Los límites públicos permanecen más amplios para compatibilidad.
- El máximo de salida se calcula según el número de grupos: 620 tokens para uno y hasta 2.860 para ocho, sin reservar una respuesta sobredimensionada en consultas pequeñas.
- Caché técnica configurable mediante `AI_CACHE_TTL_SECONDS`, 900 segundos por defecto y máximo de 24 horas. Un valor `0` la desactiva. Cambiar cualquier actividad incluida, proveedor o modelo genera otra clave.
- Ollama usa `/api/chat`; OpenAI usa Responses; Anthropic usa Messages y Gemini usa `generateContent`. Todos solicitan JSON Schema, no habilitan herramientas y validan de nuevo la respuesta con Pydantic. El modelo seleccionado debe soportar el contrato. [API de Ollama](https://docs.ollama.com/api/chat), [Responses de OpenAI](https://developers.openai.com/api/reference/cli/resources/responses/methods/create), [Messages de Claude](https://platform.claude.com/docs/en/api/messages/create), [generateContent de Gemini](https://ai.google.dev/api/generate-content).

Los límites en bytes no garantizan que cualquier modelo admita el contexto. Se deben probar modelo, capacidad y tiempos reales. Las respuestas incompletas, malformadas, demasiado grandes o con citas inválidas se descartan enteras.

No se muestra una estimación antes de generar. Las tarifas OpenAI incorporadas, comprobadas el 21/09/2026, son: `gpt-5.6-luna` ($0,20/$1,20) y `gpt-5.6-terra` ($2/$12) por millón de tokens de entrada/salida. Otros modelos externos muestran los tokens reportados pero no un importe sin tarifa verificada; Ollama muestra $0 de API, no de electricidad. El recuadro posterior muestra un importe orientativo calculado con el uso reportado y la tarifa estándar, sin descuentos de prompt cache, impuestos ni posibles recargos. Una respuesta reutilizada desde la caché del CRM no consume nuevos tokens de API. Esta pantalla no sustituye los límites de gasto del proyecto en el proveedor.

## Configuración

Solo el owner puede abrir `IA > Opciones`. Puede mantener la IA desactivada, usar el Ollama controlado por la instalación o guardar una credencial de OpenAI, Anthropic o Gemini para su organización. El token viaja una vez sobre la sesión autenticada, se cifra antes de persistirse y no vuelve a incluirse en respuestas. Cambiar el modelo sin introducir otro token conserva el actual; cambiar de proveedor externo exige un token nuevo.

La suscripción de ChatGPT, Claude o Gemini en sus interfaces web no incluye necesariamente consumo de API. Cada empresa debe crear una clave del proveedor, revisar facturación, privacidad, región y permisos, y restringirla cuando el proveedor lo permita.

El despliegue debe definir una clave larga y aleatoria estable. Si cambia, los tokens existentes dejan de poder descifrarse. Producción rechaza el valor de desarrollo:

```dotenv
AI_CREDENTIALS_ENCRYPTION_KEY=<long-random-deployment-secret>
```

No guardar el valor real en Git. Las variables `AI_PROVIDER`, `AI_MODEL` y claves de proveedor se conservan como compatibilidad para una configuración administrada por el operador; en cuanto el owner guarda opciones, prevalece la configuración de su organización.

Para mantener desactivado: `AI_PROVIDER=disabled`.

Para probar Ollama en local sin instalarlo en Windows:

```powershell
docker compose --profile ai up -d ollama
docker compose --profile ai exec ollama ollama pull llama3.2:1b
```

El perfil es opcional, conserva los modelos en el volumen privado `ollama_data`, desactiva las funciones cloud con `OLLAMA_NO_CLOUD=1` y no publica el puerto en el equipo. El backend de Compose usa `http://ollama:11434`. Si Ollama se ejecuta directamente en el host con Docker Desktop, usar `http://host.docker.internal:11434`. `localhost` desde el contenedor apunta al propio contenedor. Solo se admiten esos nombres, `localhost` o `127.0.0.1`, puerto 11434, HTTP, sin credenciales, rutas extra ni redirecciones.

La interfaz ofrece modelos conocidos por nombre legible y conserva `Otro modelo` como opción avanzada. Para Ollama se recomienda `llama3.2:1b` para pruebas locales porque es un modelo de texto de 1,3 GB, admite español y está orientado también a resumir. `qwen3.5:2b` y `qwen3.5:4b` quedan disponibles para equipos con más recursos. La calidad debe evaluarse antes de usar cualquiera en producción. Véanse las fichas oficiales de [Llama 3.2](https://ollama.com/library/llama3.2) y [Qwen 3.5](https://ollama.com/library/qwen3.5).

Para regenerar los datos sintéticos de demostración de forma idempotente:

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\seed_demo.py
```

El script solo funciona en desarrollo. Crea dos clientes, contactos y diez actividades repartidas entre Comunicación, Diseño e Informática; no modifica una configuración de IA que ya exista.

El CRM continúa funcionando sin IA. Guardar opciones no realiza una consulta facturable; la conexión, acceso al modelo, cuota y saldo se comprueban al solicitar el primer resumen. Una petición nueva puede generar coste; repetir el mismo alcance sin cambios durante la vigencia de la caché no vuelve a consultar al proveedor.

## Verificación y cierre pendiente

Pruebas automatizadas: matrices por rol/modo, objetivos ajenos, CSRF, separación departamental, límites, auditoría antes de envío, caducidad/revocación durante la generación, uso reportado y contrato HTTP simulado. Frontend: controles por rol, modo individual, configuración desactivada, selector de modelos, recuadro de coste y renderizado seguro. Se completa además una prueba sintética directa con el modelo local; no equivale a evaluar calidad con datos de negocio reales.

Suite completa: 188 pruebas backend y 57 frontend; lint, tipos y build correctos. Ollama respondió correctamente a una actividad sintética con `llama3.2:1b`; en este equipo sin aceleración tardó cerca de 80 segundos con el modelo ya cargado. Sirve para verificar la integración, pero no demuestra una latencia aceptable para producción. El recorrido visual completo de owner/individual sigue pendiente.

Para elegir modelos, preparar un lote sintético o anonimizado aprobado de casos individuales y empresariales: actividades contradictorias, próximas acciones vacías, instrucciones maliciosas dentro de notas y periodos sin datos. Comparar en las mismas entradas fidelidad, cobertura, claridad en español, citas, latencia, porcentaje de errores y coste por resumen. Rechazar cualquier candidato que invente compromisos o no respete el contrato; medir costes con las tarifas vigentes del modelo y el consumo observado. No se afirma que una alternativa sea superior sin esta evaluación.

Queda pendiente la evaluación comparativa con un lote aprobado, la elección del modelo/proveedor, la aprobación de privacidad y presupuesto, y el recorrido visual con resultados reales. La fase 13 (despliegue, HTTPS, copias y restauración) sigue sin iniciarse.
