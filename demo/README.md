# Demo del CRM Platform

La demo utiliza el mismo frontend Next.js, las mismas rutas y los mismos componentes que el CRM principal. Con `DEMO_MODE=true`, las respuestas proceden de datos sintéticos alojados en memoria dentro del proceso Next.js. No se consulta PostgreSQL ni ningún proveedor de IA.

Desde `frontend/`, ejecuta `npm.cmd run demo` y abre `http://127.0.0.1:4173`. Como alternativa, desde la raíz del repositorio ejecuta `docker compose -f compose.demo.yaml up --build -d`.

Los cambios se guardan temporalmente por navegador en la memoria del servidor. Al reiniciar Next.js o transcurrir 24 horas se recuperan los datos iniciales. No se necesita base de datos, backend, cuenta, token ni servicio externo. El resumen de IA se genera localmente a partir de las actividades sintéticas.

El despliegue de la demo solo necesita el contenedor Next.js. No se levanta FastAPI, PostgreSQL ni Ollama. Cada petición sigue consumiendo recursos del servidor Next.js: no existe coste cero si se publica en un servidor de pago. Mantén una sola instancia de la demo, porque el estado temporal reside en su memoria.
