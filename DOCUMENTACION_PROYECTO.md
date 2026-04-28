# Documentación técnica — Portal de Exportación

> Este documento explica la estructura y el funcionamiento del proyecto desde el punto de vista técnico. Sirve como referencia para entender cómo está organizado el código, qué papel cumple cada fichero y cómo se conectan las piezas entre sí. No es un manual de usuario, sino una guía para quien tenga que mantener o ampliar el proyecto.

---

## Índice

1. [Visión general del proyecto](#1-visión-general-del-proyecto)
2. [Estructura de carpetas](#2-estructura-de-carpetas)
3. [Configuración global](#3-configuración-global)
4. [Aplicación `comercial`](#4-aplicación-comercial)
5. [Aplicación `clientes`](#5-aplicación-clientes)
6. [Aplicación `calidad`](#6-aplicación-calidad)
7. [Conexión con Dataverse](#7-conexión-con-dataverse)
8. [Integración con el endpoint de IA](#8-integración-con-el-endpoint-de-ia)
9. [Integración con Power Automate](#9-integración-con-power-automate)
10. [Internacionalización (i18n) del portal de clientes](#10-internacionalización-i18n-del-portal-de-clientes)
11. [Autenticación](#11-autenticación)
12. [Plantillas y frontend](#12-plantillas-y-frontend)
13. [Flujo de una petición HTTP](#13-flujo-de-una-petición-http)
14. [Variables de entorno](#14-variables-de-entorno)
15. [Comandos de desarrollo](#15-comandos-de-desarrollo)
16. [Dependencias](#16-dependencias)
17. [Pendiente de implementar](#17-pendiente-de-implementar)

---

> **Última actualización:** 2026-04-28 — Spinner en botón "Derivar a Calidad"; campo `gfit_respondido` en materiales (indicador visual de productos ya respondidos); envío de respuesta marca automáticamente los materiales del subgrupo como respondidos en Dataverse; modal de respuesta individual por producto con flujo completo (IA + adjuntos + envío)

---

## 1. Visión general del proyecto

El proyecto es una aplicación web Django con **tres portales diferenciados**:

| Portal | Acceso | Función principal |
|--------|--------|-------------------|
| **Portal Comercial** | Interno (staff de ventas) | Gestionar incidencias: ver, filtrar, reclasificar gravedades y causas, ajustar tono con IA, derivar a Calidad, enviar respuesta al cliente por email |
| **Portal Clientes** | Externo (clientes) | Crear incidencias vía formulario y consultar el estado de las suyas por correo. Formulario disponible en ES/EN |
| **Portal Calidad** | Interno (equipo de calidad) | Ver y gestionar los productos derivados a calidad: editar causas y gravedades, generar respuesta interna con IA |

La fuente de datos es **Microsoft Dataverse** (conectado). Toda la lectura y escritura de incidencias, causas y materiales pasa por `comercial/api/dataverse.py`.

---

## 2. Estructura de carpetas

```
ProyectoExportacion/
│
├── manage.py                          # Punto de entrada Django
├── requirements.txt                   # Dependencias Python
├── .env                               # Variables sensibles (NO en git)
├── .gitignore
│
├── ProyectoExportacionDjango/         # Configuración global del PROYECTO
│   ├── settings.py                    # Ajustes principales
│   ├── urls.py                        # Router raíz de URLs
│   ├── wsgi.py
│   └── asgi.py
│
├── comercial/                         # App del portal interno (staff ventas)
│   ├── views.py                       # Lógica de vistas
│   ├── urls.py                        # URLs del portal comercial
│   ├── context_processors.py          # Datos globales para templates comercial
│   ├── api/
│   │   └── dataverse.py               # Cliente Dataverse (única fuente de verdad)
│   ├── templates/comercial/
│   │   ├── base.html
│   │   ├── login.html
│   │   ├── dashboard.html
│   │   └── detalle_incidencia.html
│   └── migrations/
│
├── clientes/                          # App del portal externo (clientes)
│   ├── views.py
│   ├── urls.py
│   ├── i18n.py                        # Diccionario de traducciones ES/EN + get_lang()
│   ├── context_processors.py          # Inyecta t y lang a todos los templates de clientes
│   ├── templates/clientes/
│   │   ├── base.html                  # Incluye selector de idioma (globo ES/EN)
│   │   ├── portal.html
│   │   ├── nueva_incidencia.html      # Formulario bilingüe
│   │   └── mis_incidencias.html
│   └── migrations/
│
├── calidad/                           # App del portal interno (equipo calidad)
│   ├── views.py
│   ├── urls.py
│   ├── templates/calidad/
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   └── detalle_incidencia.html    # Doble select causas + generador IA
│   └── migrations/
│
└── venv/                              # Entorno virtual Python (no en git)
```

---

## 3. Configuración global

### `ProyectoExportacionDjango/settings.py`

```python
INSTALLED_APPS = [
    ...
    'comercial',   # Portal interno ventas
    'clientes',    # Portal externo clientes
    'calidad',     # Portal interno calidad
]

LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'Europe/Madrid'
USE_I18N = True

TEMPLATES = [{
    ...
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
            'clientes.context_processors.clientes_i18n',  # inyecta t y lang a clientes
        ],
    },
}]
```

El context processor `clientes_i18n` se ejecuta en todas las vistas del proyecto e inyecta las variables `t` (diccionario de traducciones según el idioma activo) y `lang` (`'es'` o `'en'`). Solo afecta visualmente a los templates de `clientes/` que usan `{{ t.xxx }}`.

### `ProyectoExportacionDjango/urls.py`

```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/login/')),
    path('', include('comercial.urls', namespace='comercial')),
    path('clientes/', include('clientes.urls', namespace='clientes')),
    path('calidad/', include('calidad.urls', namespace='calidad')),
]
```

---

## 4. Aplicación `comercial`

### URLs (`comercial/urls.py`)

| URL | Vista | Nombre |
|-----|-------|--------|
| `/login/` | `login_view` | `comercial:login` |
| `/logout/` | `logout_view` | `comercial:logout` |
| `/dashboard/` | `dashboard` | `comercial:dashboard` |
| `/ajustar-tono/` | `ajustar_tono` | `comercial:ajustar_tono` |
| `/incidencia/<id>/` | `detalle_incidencia` | `comercial:detalle_incidencia` |
| `/incidencia/<id>/gravedades/` | `actualizar_gravedades` | `comercial:actualizar_gravedades` |
| `/incidencia/<id>/finalizar/` | `marcar_finalizada` | `comercial:marcar_finalizada` |
| `/incidencia/<id>/enviar-respuesta/` | `enviar_respuesta` | `comercial:enviar_respuesta` |
| `/material/<id>/derivar-calidad/` | `derivar_material_calidad` | `comercial:derivar_material_calidad` |

### Vistas (`comercial/views.py`)

**`dashboard`**
- Requiere login (`@login_required`)
- Llama a `DataverseClient().get_tickets()` para obtener todas las incidencias
- Calcula totales por estado (Pendiente / Procesando / Finalizada) y derivadas a Calidad
- Renderiza `dashboard.html` con tabla (DataTables) y tarjetas de filtro rápido

**`detalle_incidencia`**
- Recibe `incidencia_id` (GUID de Dataverse) por URL
- Llama a `DataverseClient().get_ticket_detail(id)` → incidencia + grupos por causa + mapa nombre→ID
- Llama a `DataverseClient().get_causes_catalog()` → catálogo de causas activas para los selects
- Detecta productos con sufijo `' [REVISAR]'` en `gfit_problema` (productos cuya causa general fue modificada por el cliente): activa el badge de aviso y bloquea el envío del email mientras no se corrijan
- Renderiza `detalle_incidencia.html` con `causas_catalogo_json` y `causa_id_map_json`
- Cada fila de producto muestra `cantidad` (incidenciada) y `cantidad_total` (stock total) para comparación visual
- Cada producto tiene un botón toggle "Calidad" que llama a `derivar_material_calidad`; la fila recibe borde naranja izquierdo al marcarse. El botón muestra un spinner durante la petición y se deshabilita hasta que termina
- Productos con respuesta enviada muestran un badge verde "Respondido" y fondo verde suave (`tr.respondida`). El estado viene del campo `gfit_respondido` de Dataverse y también se aplica visualmente en el momento del envío sin recargar
- Cada fila de producto tiene un botón `↩` (reply) que abre un modal individual con el flujo completo de respuesta (generar con IA, adjuntar archivos, enviar). El modal es único y se reutiliza para cualquier producto

**`actualizar_gravedades`** (POST, AJAX)
- Recibe `{productos: [{id, codigo, gravedad, causa_id, causa_nombre, causa_catalog_id, causa_id_original, problema}]}`
- Si la causa no existe aún como `ticket_cause` en Dataverse, la crea automáticamente con `create_ticket_cause`
- Actualiza gravedad, causa y (si `problema` no es null) el campo `gfit_problema` de cada material
- Si el material cambió de causa y la causa original quedó sin materiales, la elimina con `delete_ticket_cause_if_empty`
- **También la usa la app calidad** (ver sección 6)

**`marcar_finalizada`** (POST, AJAX)
- El botón verde "Marcar como Finalizada" abre un **modal Bootstrap** de confirmación antes de llamar al endpoint
- Si se confirma: actualiza `gfit_estado` a `347780002` (Finalizada) en Dataverse con `update_ticket`
- Devuelve `{"ok": true}`; el JS actualiza el badge de estado y desactiva el botón sin recargar la página
- El view incluye comentarios `TODO` marcando los puntos de extensión futura (contador de finalizadas, auditoría de respuesta válida, notificación al cliente)

**`derivar_material_calidad`** (POST, AJAX)
- Recibe `{derivar: bool, ticket_id: str}`
- Llama a `DataverseClient().derivar_material(material_id, derivar)` → PATCH `gfit_derivadacalidad` del material
- Si `derivar=true`, llama también a `DataverseClient().derivar_ticket(ticket_id, True)`
- Si `derivar=false` y el ticket ya no tiene materiales derivados, llama a `derivar_ticket(ticket_id, False)` para desmarcar el ticket

**`ajustar_tono`** (POST, AJAX)
- Recibe `{texto, tono, cliente, idioma, gravedad, causas}` en JSON
- Llama al endpoint interno de IA (ver sección 8)
- Devuelve `{"texto": "texto reescrito"}`

**`enviar_respuesta`** (POST, multipart/form-data, AJAX)
- Recibe `texto`, `adjuntos[]` (archivos opcionales) y `material_ids[]` (IDs de materiales involucrados en la respuesta)
- Lee `destinatario`, `conversation_id` y `message_id` frescos de Dataverse
- Valida que el ticket tenga `message_id` (solo los tickets que entraron por email)
- Codifica cada adjunto en base64 y envía a `POWER_AUTOMATE_EMAIL_REPLY_URL`
- Tras envío exitoso, llama a `DataverseClient().marcar_materiales_respondidos(material_ids)` para PATCH `gfit_respondido = true` en cada material. Si este paso falla se loguea como warning pero no se revierte el envío
- El frontend puede invocar este endpoint tanto desde el editor de subgrupo (todos los materiales del subgrupo) como desde el modal de producto individual (un único `material_id`)

---

## 5. Aplicación `clientes`

### URLs (`clientes/urls.py`)

| URL | Vista | Nombre |
|-----|-------|--------|
| `/clientes/` | `portal` | `clientes:portal` |
| `/clientes/nueva-incidencia/` | `nueva_incidencia` | `clientes:nueva_incidencia` |
| `/clientes/mis-incidencias/` | `mis_incidencias` | `clientes:mis_incidencias` |

### Vistas (`clientes/views.py`)

**`portal`** — página de bienvenida sin lógica.

**`nueva_incidencia`**
- **GET**: lee parámetros de URL para prellenar el formulario; llama a `get_lang(request)` para persistir `?lang=` en sesión
- Llama a `DataverseClient().get_causes_catalog()` → catálogo bilingüe para los selects
- Enriquece los productos del prefill con `causageneral` (ES, clave interna) y `gravedad`
- Construye `causas_bilingues` (lista de `{es, en}`) para el select del formulario
- **POST**: valida empresa + correo + al menos un producto, agrupa por causa, llama a Power Automate
- Los mensajes de error (`messages.error`) usan las cadenas del diccionario `UI[lang]`

Formato de URL para prellenar el formulario desde el email del agente:
```
/clientes/nueva-incidencia/?lang=en&empresa=X&correo=Y&conv=Z
  &p0_codigo=A&p0_nombre=B&p0_lote=C&p0_cantidad=10&p0_albaran=D
  &p0_fecha=YYYY-MM-DD&p0_problema=F&p0_causa=G&p0_gravedad=H
  &p1_codigo=...
```

Los productos se indexan desde `p0_*`, `p1_*`, `p2_*`... sin límite.

**`mis_incidencias`**
- **GET**: formulario para introducir el correo
- **POST**: llama a `DataverseClient().get_tickets()` y filtra por correo del cliente

### Funciones auxiliares

| Función | Descripción |
|---------|-------------|
| `_leer_productos_url(request)` | Lee productos prefijados por URL (`?p0_codigo=...`) |
| `_leer_productos_post(request)` | Reconstruye la lista de productos desde el POST |
| `_causas_generales_bilingues(causas_catalogo)` | Devuelve lista ordenada de pares únicos `{es, en}` de causageneral; `es` es siempre la clave interna enviada al backend |

---

## 6. Aplicación `calidad`

### URLs (`calidad/urls.py`)

| URL | Vista | Nombre |
|-----|-------|--------|
| `/calidad/dashboard/` | `dashboard` | `calidad:dashboard` |
| `/calidad/incidencia/<id>/` | `detalle_incidencia` | `calidad:detalle_incidencia` |
| `/calidad/incidencia/<id>/guardar/` | `actualizar_gravedades` (de comercial) | `calidad:actualizar_gravedades` |
| `/calidad/generar-respuesta/` | `generar_respuesta` | `calidad:generar_respuesta` |

La URL de guardar reutiliza directamente la view `comercial.views.actualizar_gravedades` (misma lógica Dataverse, sin duplicar código).

### Vistas (`calidad/views.py`)

**`dashboard`**
- Llama a `DataverseClient().get_tickets_calidad()` → solo tickets con `gfit_derivadacalidad = true`
- Calcula totales por estado
- Renderiza `calidad/dashboard.html`

**`detalle_incidencia`**
- Llama a `DataverseClient().get_ticket_detail_calidad(id)` → solo materiales con `gfit_derivadacalidad = true`
- Llama a `DataverseClient().get_causes_catalog()` → catálogo para los selects de causa
- Detecta productos con sufijo `' [REVISAR]'` (mismo mecanismo que comercial)
- Pasa `causas_catalogo_json` y `causa_id_map_json` al template para el doble select de causas
- Renderiza `calidad/detalle_incidencia.html`

**`generar_respuesta`** (POST, AJAX)
- Llama al endpoint de IA de calidad (`CALIDAD_AI_ENDPOINT`)
- Payload: `{texto, cliente, idioma, gravedad, causas: [{nombre}]}`
- Devuelve `{"texto": "respuesta generada"}`

### Template `calidad/detalle_incidencia.html`

Incluye, igual que el template de comercial:
- **Doble select de causa** por producto: "General" (causageneral) + "Específ." (causa específica del catálogo)
- **Select de gravedad** editable (Leve / Moderada / Grave) con color dinámico
- **Botón "Guardar cambios"** por subgrupo (aparece al detectar cambios); llama a `calidad:actualizar_gravedades`
- **Toast de confirmación** al guardar correctamente (sin recargar la página)
- **Badge "Revisar causa"** en productos modificados por el cliente

La lógica JS de los selects es idéntica a la de comercial: `buildCausaGeneralOptions`, `buildCausaEspecificaOptions`, `guardarSubgrupo`, `colorearGravedad`.

---

## 7. Conexión con Dataverse

### `comercial/api/dataverse.py`

Toda la lógica de acceso a Dataverse está encapsulada en `DataverseClient`. Para cambiar de fuente de datos, solo hay que modificar este fichero.

**Autenticación**: `msal.ConfidentialClientApplication` con client credentials flow. Se pide token nuevo en cada llamada.

**Mapeos de option sets**:

```python
ESTADO_MAP = { 347780000: 'Pendiente', 347780001: 'Procesando', 347780002: 'Finalizada' }
GRAVEDAD_MAP = { 347780000: 'Leve', 347780001: 'Moderada', 347780002: 'Grave' }
IDIOMA_MAP = {
    347780000: 'Español', 347780001: 'Inglés', 347780002: 'Francés',
    347780003: 'Portugués', 347780004: 'Alemán', 347780005: 'Italiano',
}
```

**Entidades (entity set names OData v9.2)**:

| Entidad lógica | Entity set (URL) |
|----------------|-----------------|
| `gfit_qlt_ticket` | `gfit_qlt_tickets` |
| `gfit_qlt_ticket_cause` | `gfit_qlt_ticket_causes` |
| `gfit_qlt_ticket_material` | `gfit_qlt_ticket_materials` |
| `gfit_qlt_cause_catalog` | `gfit_qlt_cause_catalogs` |

**Métodos públicos**:

| Método | Descripción |
|--------|-------------|
| `get_tickets()` | Lista todas las incidencias (dashboard comercial) |
| `get_tickets_calidad()` | Lista incidencias con `gfit_derivadacalidad = true` (dashboard calidad) |
| `get_ticket_detail(ticket_id)` | Detalle completo: incidencia + causas + materiales agrupados por causa y gravedad + `all_ticket_causes` |
| `get_ticket_detail_calidad(ticket_id)` | Igual que `get_ticket_detail` pero filtrando solo materiales con `gfit_derivadacalidad = true`. También devuelve `all_ticket_causes` |
| `get_ticket_reply_data(ticket_id)` | Solo `destinatario`, `conversation_id` y `message_id` — mínimo para responder por email |
| `get_causes_catalog()` | Catálogo de causas activas ordenadas por `gfit_orden`. Devuelve `causageneral` (ES) y `causageneral_en` (EN) |
| `update_ticket(ticket_id, datos)` | PATCH genérico sobre un ticket |
| `update_material(material_id, gravedad_str, causa_id, problema)` | Actualiza gravedad, causa y opcionalmente `gfit_problema` de un material |
| `create_ticket_cause(ticket_id, nombre, catalog_cause_id)` | Crea una nueva ticket_cause y devuelve su ID |
| `delete_ticket_cause_if_empty(cause_id)` | Elimina la ticket_cause si no le quedan materiales |
| `derivar_material(material_id, derivar)` | PATCH `gfit_derivadacalidad` de un material |
| `derivar_ticket(ticket_id, derivar)` | PATCH `gfit_derivadacalidad` de un ticket |
| `has_derived_materials(ticket_id)` | Devuelve `True` si el ticket tiene al menos un material derivado a calidad |
| `marcar_materiales_respondidos(material_ids)` | PATCH `gfit_respondido = true` en cada material de la lista. Se llama tras envío exitoso de email |

### Campo `gfit_causageneral_en` en el catálogo

La entidad `gfit_qlt_cause_catalog` tiene dos campos de option set para la causa general:

| Campo Dataverse | Descripción |
|----------------|-------------|
| `gfit_causageneral` | Causa general en **español** (clave interna, se usa siempre en el backend) |
| `gfit_causageneral_en` | Causa general en **inglés** (solo para mostrar al cliente en el portal) |

Cada registro del catálogo tiene ambas asignadas. El backend siempre usa el valor ES como clave; el portal de clientes muestra el valor EN o ES según el idioma activo.

`get_causes_catalog()` devuelve por cada causa:
```python
{
    'id':              'guid',
    'nombre':          'Rotura de embalaje exterior',   # gfit_nombrecausa
    'causageneral':    'Daños de embalaje',             # ES — clave interna
    'causageneral_en': 'Packaging damage',              # EN — solo para display
    'gravedad':        'Moderada',
    'gravedad_code':   347780001,
}
```

### Estructura devuelta por `get_ticket_detail`

```python
{
    'incidencia': {
        'id', 'titulo', 'cliente', 'correo', 'empresa',
        'idioma',           # mapeado con IDIOMA_MAP
        'estado',           # mapeado con ESTADO_MAP
        'fecha',            # YYYY-MM-DD
        'conversation_id',  # para reply en email
        'message_id',       # para reply en email (puede estar vacío)
    },
    'grupos': [
        {
            'causa_id':         'guid',
            'causa_nombre':     'Presencia hueso',
            'causa_catalog_id': 'guid',
            'subgrupos': [
                {
                    'gravedad': 'Grave',            # o 'Moderada' / 'Leve'
                    'sg_key':   'abc12345-grave',   # clave única para JS
                    'productos': [
                        {
                            'id', 'nombre', 'codigo', 'cantidad', 'cantidad_total',
                            'lote', 'albaran', 'problema', 'fecha',
                            'gravedad',        # string
                            'causa_nombre',    # nombre de la ticket_cause
                            'causa_id',        # GUID de la ticket_cause
                            'causa_catalog_id',# GUID del catálogo
                            'derivada_calidad',# bool — gfit_derivadacalidad
                            'respondido',      # bool — gfit_respondido (se ha enviado respuesta al cliente para este producto)
                        }
                    ]
                }
            ]
        }
    ],
    'all_ticket_causes': { 'nombre_causa': 'ticket_cause_id', ... }
}
```

**Propiedades de navegación OData** (usan `ID` en mayúsculas — distinto a los campos de filtro):

```python
# Al crear ticket_cause:
'gfit_qlt_ticketID@odata.bind':        f'/gfit_qlt_tickets({ticket_id})'
'gfit_qlt_cause_catalogID@odata.bind': f'/gfit_qlt_cause_catalogs({catalog_cause_id})'

# Al actualizar material:
'gfit_qlt_ticket_causeID@odata.bind':  f'/gfit_qlt_ticket_causes({causa_id})'
```

> Los campos de filtro OData usan minúsculas con prefijo `_` y sufijo `_value` (`_gfit_qlt_ticketid_value`). No confundirlos con las propiedades de navegación.

**SSL**: todas las llamadas usan `verify=False` por el proxy corporativo con inspección SSL. Los warnings de urllib3 están silenciados con `urllib3.disable_warnings()`.

---

## 8. Integración con el endpoint de IA

### Ajuste de tono (portal comercial)

El comercial puede reescribir el texto de respuesta al cliente con dos tonos: **amigable** o **formal**.

- **Endpoint interno**: `http://scloudw040:1084/Endpoint_Incidencias/api/incidencias/consulta`
- **Vista Django**: `comercial:ajustar_tono` (POST, AJAX)
- **Timeout**: 120 segundos

**Payload enviado**:
```json
{
  "texto":    "Texto original del comercial",
  "tono":     "amigable",
  "cliente":  "correo@cliente.com",
  "idioma":   "Inglés",
  "gravedad": "Grave",
  "causas": [
    {
      "nombre": "Presencia hueso",
      "productos": [
        { "nombre": "Jamón moldeado", "cantidad": "3", "problema": "Descripción" }
      ]
    }
  ]
}
```

**Respuesta esperada**: `{ "content": "Texto reescrito por la IA" }`

Las causas y productos se leen de la tabla visible en pantalla (agrupando filas por la causa seleccionada en el select).

### Generación de respuesta interna (portal calidad)

El equipo de calidad puede generar un texto de respuesta interna con IA.

- **Endpoint interno**: configurable vía variable de entorno `CALIDAD_AI_ENDPOINT`
- **Vista Django**: `calidad:generar_respuesta` (POST, AJAX)
- **Timeout**: 120 segundos

**Payload enviado**:
```json
{
  "texto":    "Contexto inicial o nombre de causa",
  "cliente":  "correo@cliente.com",
  "idioma":   "Inglés",
  "gravedad": "Grave",
  "causas":   [{ "nombre": "Presencia hueso" }]
}
```

---

## 9. Integración con Power Automate

### Creación de incidencias (portal clientes)

- **Variable de entorno**: `POWER_AUTOMATE_INCIDENCIAS_URL`
- **Vista**: `clientes:nueva_incidencia`
- **Payload enviado**:
```json
{
  "empresa": "Mercadona SA",
  "correo":  "cliente@ejemplo.com",
  "conversation_id": "CONV-2026-001",
  "causas": [
    {
      "nombre": "Presencia hueso",
      "productos": [
        {
          "codigo": "LOM-040", "nombre": "Lomo Embuchado 200g",
          "lote": "L2026-07", "cantidad": "50", "albaran": "ALB-2026-099",
          "fecha": "2026-04-01", "problema": "Envase roto", "gravedad": 347780002
        }
      ]
    }
  ]
}
```

Los productos se agrupan por causa antes de enviar. Si el cliente seleccionó una causa general diferente a la original (causa modificada), el `problema` lleva el sufijo `' [REVISAR]'` para que el agente comercial lo detecte.

### Respuesta por email al cliente (portal comercial)

- **Variable de entorno**: `POWER_AUTOMATE_EMAIL_REPLY_URL`
- **Vista**: `comercial:enviar_respuesta` (POST multipart/form-data)
- **Payload enviado al flow**:
```json
{
  "destinatario":    "cliente@ejemplo.com",
  "conversation_id": "CONV-2026-001",
  "message_id":      "AAMk...",
  "cuerpo":          "Estimado/a cliente...",
  "adjuntos": [
    { "Name": "informe.pdf", "ContentBytes": "<base64>" }
  ]
}
```

Los adjuntos se acumulan en el array JS `archivosAcumulados[sgKey]` antes del envío. Tras envío exitoso, el array se vacía.

**Restricción**: solo funcionan tickets que llegaron por email (tienen `gfit_messageid` en Dataverse).

**Flow de Power Automate** (`POWER_AUTOMATE_EMAIL_REPLY_URL`):

| Acción | Detalle |
|--------|---------|
| Trigger HTTP | Recibe el JSON. Trigger público (sin auth Azure AD) |
| Select | Transforma `adjuntos` aplicando `base64ToBinary(item()['ContentBytes'])` |
| Reply to an email (V3) | `Message Id` = `message_id`, `Body` = `cuerpo`, `To` = `destinatario`, `Attachments` = output Select |
| Response 200 | Confirma a Django que el envío fue correcto |

---

## 10. Internacionalización (i18n) del portal de clientes

El portal de clientes soporta **español (ES) e inglés (EN)**. El idioma se detecta en este orden de prioridad:

1. Parámetro `?lang=` en la URL (ej. `?lang=en` en el enlace del email del agente)
2. Idioma almacenado en sesión (`clientes_lang`)
3. Fallback: `es`

### Ficheros involucrados

**`clientes/i18n.py`**
- Diccionario `UI` con todas las cadenas de la interfaz en ES y EN
- Función `get_lang(request)`: lee `?lang=` de la URL, lo guarda en `request.session['clientes_lang']` y lo devuelve
- Constante `SUPPORTED = frozenset({'es', 'en'})` para validar idiomas

**`clientes/context_processors.py`**
- Lee `clientes_lang` de la sesión y devuelve `{'t': UI[lang], 'lang': lang}` a todos los templates

**`clientes/templates/clientes/base.html`**
- El atributo `<html lang="{{ lang }}">` refleja el idioma activo
- Selector de idioma en el navbar: botón dropdown con icono globo y `{{ lang|upper }}`
- Función JS `switchLang(lang)` usa `URL.searchParams.set('lang', lang)` para preservar todos los parámetros de la URL al cambiar de idioma

**`clientes/templates/clientes/nueva_incidencia.html`**
- Todos los labels, placeholders, botones y mensajes usan `{{ t.xxx }}`
- Variables JS `LANG` y `I18N` inyectadas desde Django para que el JS también tenga las traducciones
- El select de causas usa `CAUSAS_BILINGUES` (array `{es, en}`): el `value` del option es siempre el texto ES (clave interna para el backend), la etiqueta mostrada depende de `LANG`

### Causas bilingues en el formulario

El campo `gfit_causageneral_en` en Dataverse almacena la causa general en inglés. `get_causes_catalog()` lo devuelve como `causageneral_en`. La función `_causas_generales_bilingues()` en `views.py` construye la lista `[{es: '...', en: '...'}]` que se pasa al template como `causas_bilingues_json`.

La clave que se envía al backend (y que usa Power Automate para identificar la causa) es siempre el texto ES. Solo el label visible cambia según el idioma activo.

### Añadir nuevos idiomas

1. Añadir el código a `SUPPORTED` en `clientes/i18n.py`
2. Añadir la entrada al diccionario `UI`
3. Añadir el campo correspondiente en Dataverse para las causas (ej. `gfit_causageneral_fr`)
4. Actualizar `get_causes_catalog()` en `dataverse.py`
5. Añadir la opción al dropdown en `base.html`

---

## 11. Autenticación

### Situación actual

Se usa el sistema de autenticación **integrado de Django** (usuario/contraseña en base de datos SQLite). Temporal, solo para desarrollo.

- El login está en `/login/` (`comercial:login`)
- Las vistas de `comercial` y `calidad` están protegidas con `@login_required`
- El portal de `clientes` **no requiere login** — es público

### Situación futura

Está previsto sustituirlo por **Microsoft SSO (Azure AD)**. Requiere configuración adicional en el registro de aplicación Azure (distinta a la que existe para Dataverse).

```bash
python manage.py createsuperuser  # crear usuario de prueba
```

---

## 12. Plantillas y frontend

### Herencia de plantillas

```
comercial/base.html  ←  login.html
                     ←  dashboard.html          (enlace "Portal Calidad" en sidebar — temporal para pruebas)
                     ←  detalle_incidencia.html

clientes/base.html   ←  portal.html
                     ←  nueva_incidencia.html
                     ←  mis_incidencias.html

calidad/base.html    ←  dashboard.html
                     ←  detalle_incidencia.html  (enlace "Portal Comercial" en sidebar)
```

> El enlace cruzado entre portales en el sidebar de comercial es temporal para facilitar las pruebas. Se eliminará cuando se implemente el control de acceso por grupos.

Las plantillas hijas rellenan los bloques: `{% block title %}`, `{% block extra_css %}`, `{% block content %}`, `{% block extra_js %}`.

### Librerías frontend (CDN)

| Librería | Para qué |
|----------|----------|
| Bootstrap 5.3 | Estilos, grid, componentes (cards, badges, toasts, modals...) |
| Bootstrap Icons 1.11 | Iconos vectoriales |
| jQuery 3.7 | Requerido por DataTables |
| DataTables 1.13 | Tabla interactiva con paginación, búsqueda y filtros (dashboard comercial y calidad) |

### JavaScript en `detalle_incidencia.html` (comercial y calidad)

Variables globales inyectadas desde Django:

| Variable JS | Origen Django | Contenido |
|-------------|--------------|-----------|
| `TICKET_ID` | `incidencia.id` | GUID del ticket activo |
| `CAUSAS_CATALOGO` | `causas_catalogo_json` | Array de `{id, nombre, causageneral, gravedad}` del catálogo activo |
| `CAUSA_ID_MAP` | `causa_id_map_json` | Objeto `{nombre_causa: ticket_cause_id}` de todas las causas del ticket |

Funciones principales:

| Función | Descripción |
|---------|-------------|
| `buildCausaGeneralOptions(seleccionada)` | Genera `<option>` del select General a partir de `CAUSAS_GENERALES_UNICAS` |
| `buildCausaEspecificaOptions(cg, catalogId, nombre)` | Genera `<option>` del select Específica filtrando `CAUSAS_CATALOGO` por causageneral |
| `guardarSubgrupo(sgKey)` | Recoge cambios de causa y gravedad de todas las filas del subgrupo y llama al endpoint de guardar |
| `colorearGravedad(el)` | Aplica clase CSS al select de gravedad (`gravedad-grave`, `gravedad-moderada`, `gravedad-leve`) |
| `mostrarBotonGuardar(sgKey)` | Muestra el botón "Guardar cambios" al detectar cualquier cambio en el subgrupo |
| `toggleDerivarCalidad(btn, materialId)` | Marca/desmarca un material individual para calidad. Muestra spinner dentro del botón y lo deshabilita durante la petición (solo en comercial) |
| `ajustarTono(tono, sgKey, ...)` | Envía el texto al endpoint de IA y actualiza el textarea del subgrupo (solo en comercial) |
| `enviarRespuesta(sgKey)` | Envía texto + adjuntos acumulados por email via Power Automate para todos los materiales del subgrupo; tras éxito marca cada fila como `respondida` (solo en comercial) |
| `abrirResponderProducto(btn, materialId, causaNombre, gravedad)` | Abre el modal de respuesta individual precargado con los datos del producto (nombre, causa, problema, cantidad leídos del `<tr>`) (solo en comercial) |
| `ajustarTonoProducto(tono)` | Igual que `ajustarTono` pero opera sobre el textarea del modal individual y usa `_prodActual` como contexto |
| `enviarRespuestaProducto()` | Envía el email para un único material (`_prodActual.materialId`) y marca su fila como respondida |
| `generarRespuesta(sgKey, ...)` | Llama al endpoint de IA de calidad (solo en calidad) |

**Preselección de causa**: se hace por **ID del catálogo** (`data-causa-catalog-id`) y usa el nombre como fallback. Garantiza la selección correcta aunque el `gfit_name` de la ticket_cause no coincida exactamente con `gfit_nombrecausa` del catálogo.

**Detección de revisables**: al cargar la página, se revisan los `<tr data-revisable="1">`. Si existen en un subgrupo, se bloquean los botones de envío/IA de ese subgrupo hasta que el agente guarde la causa corregida.

---

## 13. Flujo de una petición HTTP

### Comercial abre el detalle de una incidencia

```
GET /incidencia/<guid>/
  → detalle_incidencia()
      → DataverseClient().get_ticket_detail(id)
          → GET gfit_qlt_tickets(<id>)
          → GET gfit_qlt_ticket_causes?$filter=_gfit_qlt_ticketid_value eq <id>
          → por cada causa: GET gfit_qlt_ticket_materials?$filter=...
      → DataverseClient().get_causes_catalog()
          → GET gfit_qlt_cause_catalogs?$filter=gfit_activo eq true
      → detecta productos [REVISAR], construye grupos
      → render('detalle_incidencia.html', {...})
```

### Comercial guarda cambios de gravedad/causa

```
POST /incidencia/<guid>/gravedades/  (AJAX, JSON)
  → actualizar_gravedades()
      → por cada producto:
          → [si causa nueva] create_ticket_cause → POST gfit_qlt_ticket_causes
          → update_material → PATCH gfit_qlt_ticket_materials
          → [si cambió causa] delete_ticket_cause_if_empty
  → JsonResponse({'ok': True})
  → JS recarga la página
```

### Calidad guarda cambios de causa/gravedad

```
POST /calidad/incidencia/<guid>/guardar/  (AJAX, JSON)
  → actualizar_gravedades()    ← misma view que comercial
      → [misma lógica Dataverse]
  → JsonResponse({'ok': True})
  → JS muestra toast de confirmación (sin recargar)
```

### Comercial deriva un material a calidad

```
POST /material/<guid>/derivar-calidad/  (AJAX, JSON)
  → derivar_material_calidad()
      → DataverseClient().derivar_material(material_id, True/False)
          → PATCH gfit_qlt_ticket_materials(<id>) {gfit_derivadacalidad: bool}
      → [si derivar=True]  DataverseClient().derivar_ticket(ticket_id, True)
      → [si derivar=False] DataverseClient().has_derived_materials(ticket_id)
          → [si no quedan]  DataverseClient().derivar_ticket(ticket_id, False)
  → JsonResponse({'ok': True})
  → JS actualiza el botón y el borde de la fila
```

### Comercial ajusta el tono con IA

```
POST /ajustar-tono/  (AJAX, JSON)
  → ajustar_tono()
      → POST http://scloudw040:1084/Endpoint_Incidencias/...
      → JsonResponse({'texto': datos['content']})
  → JS actualiza el textarea
```

### Comercial envía la respuesta por email (subgrupo completo)

```
POST /incidencia/<guid>/enviar-respuesta/  (multipart/form-data)
  → enviar_respuesta()
      → DataverseClient().get_ticket_reply_data(id) → {destinatario, conversation_id, message_id}
      → valida message_id
      → codifica adjuntos en base64
      → POST POWER_AUTOMATE_EMAIL_REPLY_URL
      → DataverseClient().marcar_materiales_respondidos([id1, id2, ...])
          → por cada id: PATCH gfit_qlt_ticket_materials(<id>) {gfit_respondido: true}
  → JsonResponse({'ok': True})
  → JS marca cada fila del subgrupo con clase 'respondida' + badge verde
```

### Comercial responde a un producto individual (modal)

```
[Click en botón ↩ de la fila]
  → abrirResponderProducto(btn, materialId, causaNombre, gravedad)
      → lee data-nombre / data-problema / data-cantidad del <tr>
      → rellena el modal con el texto por defecto y los datos del producto
      → abre #modalResponderProducto

[Opcional: Tono amigable / Tono serio]
  → ajustarTonoProducto(tono)
      → POST /ajustar-tono/   ← mismo endpoint que el subgrupo
      → actualiza textarea del modal

[Enviar al cliente]
  → enviarRespuestaProducto()
      → POST /incidencia/<guid>/enviar-respuesta/
             con material_ids[] = [materialId]
      → misma view que el subgrupo — marca ese único material como respondido
      → JS marca la fila en la tabla como 'respondida'
```

### Cliente envía una incidencia

```
POST /clientes/nueva-incidencia/
  → nueva_incidencia()
      → get_lang(request)  → persiste idioma en sesión
      → valida empresa, correo + al menos un producto
      → agrupa productos por causa, añade [REVISAR] si causa fue modificada
      → POST POWER_AUTOMATE_INCIDENCIAS_URL
      → render('nueva_incidencia.html', {'enviado': True})
```

### Cliente cambia de idioma

```
GET /clientes/nueva-incidencia/?lang=en&empresa=X&...
  → nueva_incidencia()
      → get_lang(request)
          → request.session['clientes_lang'] = 'en'
      → render(...)
          → context_processor clientes_i18n lee sesión → devuelve t=UI['en'], lang='en'
  → Template usa {{ t.xxx }} y LANG='en' en JS para mostrar causas en inglés
```

---

## 14. Variables de entorno

Almacenadas en `.env` en la raíz. **No se suben a git**.

| Variable | Descripción |
|----------|-------------|
| `AZURE_CLIENT_ID` | Client ID del registro de aplicación Azure |
| `AZURE_CLIENT_SECRET` | Secret del registro de aplicación Azure |
| `AZURE_TENANT_ID` | Tenant ID de la organización Azure |
| `DATAVERSE_URL` | URL base de la organización Dataverse (ej. `https://gf-it-dev.crm4.dynamics.com`) |
| `POWER_AUTOMATE_INCIDENCIAS_URL` | Flow de PA para creación de incidencias (portal clientes) |
| `POWER_AUTOMATE_EMAIL_REPLY_URL` | Flow de PA para reply por email al cliente (portal comercial). Trigger público sin auth |
| `CALIDAD_AI_ENDPOINT` | Endpoint de IA para generación de respuestas internas de calidad |

---

## 15. Comandos de desarrollo

```bash
# Activar el entorno virtual (necesario siempre)
venv\Scripts\activate          # Windows PowerShell
source venv/bin/activate        # Linux/Mac

# Arrancar el servidor de desarrollo
python manage.py runserver

# Actualizar requirements.txt tras instalar nuevas librerías
venv\Scripts\pip freeze > requirements.txt

# Crear un usuario de prueba para los portales internos
python manage.py createsuperuser

# Git — operaciones habituales
git status
git add <fichero>
git commit -m "mensaje"
git push -u origin <rama>
```

---

## 16. Dependencias

Definidas en `requirements.txt`:

| Paquete | Para qué |
|---------|----------|
| `django` | Framework web principal |
| `python-dotenv` | Cargar variables de entorno desde `.env` |
| `requests` | Llamadas HTTP a Dataverse, endpoint IA y Power Automate |
| `urllib3` | Control de warnings SSL (`verify=False`) |
| `msal` | Autenticación Microsoft Azure AD (client credentials flow) |

---

## 17. Pendiente de implementar

| Funcionalidad | Bloqueado por | Dónde implementar |
|---------------|--------------|-------------------|
| Login con Microsoft SSO | Configuración Azure AD (distinta a la de Dataverse) | `comercial/views.py`, `settings.py` |
| Enviar email desde ticket sin `message_id` | Tickets creados manualmente no tienen hilo de email origen; habría que crear un email nuevo en lugar de reply | `comercial/views.py:enviar_respuesta` |
| Traducción del portal de clientes a más idiomas (FR, PT...) | Añadir campo `gfit_causageneral_fr` etc. en Dataverse y actualizar `i18n.py` y `dataverse.py` | `clientes/i18n.py`, `dataverse.py`, `base.html` |
| Verificar códigos numéricos de `IDIOMA_MAP` | Los valores de `gfit_idioma` dependen del orden del option set en Dataverse — comprobar con `print(t.get('gfit_idioma'))` en `get_ticket_detail` | `comercial/api/dataverse.py` |
| Efectos al finalizar incidencia (fase 2) | Incrementar contador cliente, marcar respuesta como válida en tabla de auditoría, notificar por email | `comercial/views.py:marcar_finalizada` |
