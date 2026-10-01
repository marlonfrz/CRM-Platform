# Versionado y funcionalidades opcionales

## Una única línea de producto

El CRM mantiene un único repositorio y una secuencia común de releases. No se crean ramas permanentes, imágenes recompiladas ni copias del código por cliente. Una release produce las mismas imágenes de frontend y backend para todas las instalaciones.

Cada instalación puede permanecer temporalmente en una versión distinta durante un despliegue escalonado, pero todas deben avanzar dentro de una ventana de soporte definida. Las correcciones de seguridad se aplican a todas las instalaciones soportadas.

## Cómo clasificar una petición de cliente

1. **Configuración:** cambia textos, correo, proveedor de IA, límites o apariencia sin alterar reglas de negocio. Se resuelve mediante configuración por organización.
2. **Funcionalidad reutilizable y opcional:** aporta valor a más de una empresa, pero no todas la necesitan. Se incorpora al núcleo detrás de una capacidad habilitable.
3. **Integración externa:** conecta un ERP, proveedor o formato propio. Se implementa mediante un adaptador con contrato estable y configuración por instalación.
4. **Desarrollo exclusivo no reutilizable:** solo se acepta con mantenimiento separado. La preferencia sigue siendo encapsularlo como módulo opcional; un fork permanente es el último recurso.

## Capacidades opcionales

Cuando aparezca la primera necesidad real se añadirá un catálogo tipado de capacidades y su estado por organización. El backend comprobará la capacidad además de los roles y permisos; ocultar un botón en frontend nunca será el control autoritativo.

Ejemplo conceptual:

```text
organization_features
  organization_id
  feature_key
  enabled
  configuration
  updated_at
```

Las capacidades tendrán un identificador estable, valor predeterminado seguro y pruebas con el estado activado y desactivado. Las migraciones de sus tablas forman parte de la release común aunque la función esté deshabilitada, evitando esquemas diferentes por cliente.

## Relación entre versión y capacidad

La versión expresa qué código está instalado; la capacidad expresa qué puede utilizar esa organización:

```text
Empresa A → release 1.4.0 → reporting avanzado activado
Empresa B → release 1.4.0 → reporting avanzado desactivado
Empresa C → release 1.3.2 → pendiente de actualización controlada
```

No se publicarán versiones como `1.4.0-cliente-a`. Los cambios incompatibles siguen versionado semántico, migraciones explícitas y notas de release. Una capacidad experimental permanece desactivada por defecto hasta completar permisos, auditoría, pruebas, documentación y rollback.

## Facturación y licencias

Una capacidad técnica no implica todavía un sistema comercial de planes. Si más adelante se venden módulos, el entitlement podrá proceder de una licencia firmada o de un servicio de control, pero el CRM debe seguir aplicando la decisión en backend y conservar un comportamiento seguro cuando ese servicio no esté disponible.
