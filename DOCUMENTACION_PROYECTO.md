# Documentación técnica — Portal de Exportación

> Este documento explica la estructura y el funcionamiento del proyecto desde el punto de vista técnico. Sirve como referencia para entender cómo está organizado el código, qué papel cumple cada fichero y cómo se conectan las piezas entre sí. No es un manual de usuario, sino una guía para quien tenga que mantener o ampliar el proyecto.

---

## Índice

1. [Visión general del proyecto](#1-visión-general-del-proyecto)
2. [Estructura de carpetas](#2-estructura-de-carpetas)
3. [Configuración global](#3-configuración-global)
4. [Aplicación `comercial`](#4-aplicación-comercial)
5. [Aplicación `clientes`](#5-aplicación-clientes)
6. [Conexión con Dataverse](#6-conexión-con-dataverse)
7. [Integración con el endpoint de IA](#7-integración-con-el-endpoint-de-ia)
8. [Integración con Power Automate](#8-integración-con-power-automate)
9. [Autenticación](#9-autenticación)
10. [Plantillas y frontend](#10-plantillas-y-frontend)
11. [Flujo de una petición HTTP](#11-flujo-de-una-petición-http)
12. [Variables de entorno](#12-variables-de-entorno)
13. [Comandos de desarrollo](#13-comandos-de-desarrollo)
14. [Dependencias](#14-dependencias)
15. [Pendiente de implementar](#15-pendiente-de-implementar)

---

> **Última actualización:** 2026-04-22 — Envío de email de respuesta al cliente con adjuntos

---

## 1. Visión general del proyecto

El proyecto es una aplicación web Django con **dos portales diferenciados**:

| Portal | Acceso | Función principal |
|--------|--------|-------------------|
| **Portal Comercial** | Interno (staff de ventas) | Gestionar incidencias: ver, filtrar, reclasificar gravedades y causas, ajustar tono con IA, derivar a Calidad |
| **Portal Clientes** | Externo (clientes) | Crear incidencias vía formulario y consultar el estado de las suyas por correo |

La fuente de datos es **Microsoft Dataverse** (ya conectado). Toda la lectura y escritura de incidencias, causas y materiales pasa por `comercial/api/dataverse.py`.

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
├── comercial/                         # App del portal interno (staff)
│   ├── views.py                       # Lógica de vistas
│   ├── urls.py                        # URLs del portal comercial
│   ├── api/
│   │   └── dataverse.py               # Cliente Dataverse (activo)
│   ├── templates/comercial/
│   │   ├── base.html                  # Plantilla base del portal comercial
│   │   ├── login.html                 # Pantalla de login
│   │   ├── dashboard.html             # Listado de incidencias con filtros
│   │   └── detalle_incidencia.html    # Detalle + editor de respuesta + IA
│   └── migrations/
│
├── clientes/                          # App del portal externo (clientes)
│   ├── views.py                       # Lógica de vistas
│   ├── urls.py                        # URLs del portal clientes
│   ├── templates/clientes/
│   │   ├── base.html                  # Plantilla base del portal clientes
│   │   ├── portal.html                # Página de bienvenida
│   │   ├── nueva_incidencia.html      # Formulario de nueva incidencia
│   │   └── mis_incidencias.html       # Consulta de incidencias por correo
│   └── migrations/
│
└── venv/                              # Entorno virtual Python (no en git)
```

---

## 3. Configuración global

### `ProyectoExportacionDjango/settings.py`

Fichero central de configuración. Los ajustes más relevantes:

```python
INSTALLED_APPS = [
    ...
    'comercial',   # Portal interno
    'clientes',    # Portal externo
]

LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'Europe/Madrid'

# Credenciales Azure / Dataverse (cargadas desde .env)
AZURE_CLIENT_ID     = os.getenv('AZURE_CLIENT_ID', '')
AZURE_CLIENT_SECRET = os.getenv('AZURE_CLIENT_SECRET', '')
AZURE_TENANT_ID     = os.getenv('AZURE_TENANT_ID', '')
DATAVERSE_URL       = os.getenv('DATAVERSE_URL', '')

# Power Automate
POWER_AUTOMATE_INCIDENCIAS_URL = os.getenv('POWER_AUTOMATE_INCIDENCIAS_URL', '')
POWER_AUTOMATE_EMAIL_REPLY_URL = os.getenv('POWER_AUTOMATE_EMAIL_REPLY_URL', '')
```

### `ProyectoExportacionDjango/urls.py`

Router raíz. Redirige `/` al login y delega cada portal a su app:

```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/login/')),
    path('', include('comercial.urls', namespace='comercial')),
    path('clientes/', include('clientes.urls', namespace='clientes')),
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
| `/incidencia/<id>/derivar-calidad/` | `derivar_calidad` | `comercial:derivar_calidad` |
| `/incidencia/<id>/enviar-respuesta/` | `enviar_respuesta` | `comercial:enviar_respuesta` |

### Vistas (`comercial/views.py`)

**`dashboard`**
- Requiere login (`@login_required`)
- Llama a `DataverseClient().get_tickets()` para obtener todas las incidencias
- Calcula totales por estado (Pendiente / Procesando / Finalizada) y derivadas a Calidad
- Renderiza `dashboard.html` con la tabla (DataTables) y tarjetas de filtro

**`detalle_incidencia`**
- Recibe `incidencia_id` (GUID de Dataverse) por URL
- Llama a `DataverseClient().get_ticket_detail(id)` → devuelve incidencia, grupos por gravedad y mapa de causas
- Llama a `DataverseClient().get_causes_catalog()` → catálogo de causas activas para los selects
- Renderiza `detalle_incidencia.html`

**`actualizar_gravedades`** (POST, AJAX)
- Recibe `{productos: [{id, codigo, gravedad, causa_id, causa_nombre, causa_catalog_id, causa_id_original}]}`
- Si la causa no existe aún como `ticket_cause` en Dataverse, la crea automáticamente con `create_ticket_cause`
- Actualiza gravedad y causa de cada material en Dataverse con `update_material`
- Si el material cambió de causa y la causa original quedó sin materiales, la elimina con `delete_ticket_cause_if_empty`

**`ajustar_tono`** (POST, AJAX)
- Recibe `{texto, tono, cliente, gravedad, causas}` en JSON
- Llama al endpoint interno de IA (ver sección 7)
- Devuelve `{"texto": "texto reescrito"}` que el JS inyecta en el textarea sin recargar la página

**`enviar_respuesta`** (POST, multipart/form-data, AJAX)
- Recibe `texto` (cuerpo del email) y `adjuntos[]` (archivos opcionales, acumulados en frontend)
- Lee `destinatario`, `conversation_id` y `message_id` frescos de Dataverse con `get_ticket_reply_data`
- Valida que el ticket tenga `message_id` (solo tienen uno los tickets que entraron por email)
- Codifica cada adjunto en base64 (`Name` + `ContentBytes`) y llama a `POWER_AUTOMATE_EMAIL_REPLY_URL`
- El flow de Power Automate hace el reply al hilo de email original usando `message_id`
- Devuelve `{"ok": true}` en éxito o `{"error": "..."}` con descripción legible en caso de fallo

**`derivar_calidad`** (POST, AJAX)
- Pendiente de implementar campo en Dataverse. Actualmente devuelve `{"ok": true}` sin acción real.

---

## 5. Aplicación `clientes`

### URLs (`clientes/urls.py`)

| URL | Vista | Nombre |
|-----|-------|--------|
| `/clientes/` | `portal` | `clientes:portal` |
| `/clientes/nueva-incidencia/` | `nueva_incidencia` | `clientes:nueva_incidencia` |
| `/clientes/mis-incidencias/` | `mis_incidencias` | `clientes:mis_incidencias` |

### Vistas (`clientes/views.py`)

**`portal`**
- Página de bienvenida, sin lógica. Solo renderiza `portal.html`

**`nueva_incidencia`**
- **GET**: lee parámetros de URL para prellenar el formulario (empresa, correo, conv, productos)
- Lee el catálogo de causas desde Dataverse para rellenar los selects del formulario
- Agrupa los productos por causa antes de enviar el payload
- **POST**: valida los datos, agrupa por causa y llama a Power Automate

Formato de URL para prellenar con varios productos:
```
/clientes/nueva-incidencia/?empresa=X&correo=Y&conv=Z
  &p0_codigo=A&p0_nombre=B&p0_lote=C&p0_cantidad=10&p0_albaran=D&p0_fecha=E&p0_problema=F&p0_causa=G&p0_gravedad=H
  &p1_codigo=...
```

Los productos se indexan desde `p0_*`, `p1_*`, `p2_*`... sin límite.

**`mis_incidencias`**
- **GET**: muestra formulario para introducir el correo
- **POST**: llama a `DataverseClient().get_tickets()` y filtra por correo del cliente

---

## 6. Conexión con Dataverse

### `comercial/api/dataverse.py`

Toda la lógica de acceso a Dataverse está encapsulada en la clase `DataverseClient`. Para cambiar de fuente de datos en el futuro, solo hay que modificar este fichero.

**Autenticación**: usa `msal.ConfidentialClientApplication` con credenciales de Azure AD (client credentials flow). Se pide un token nuevo en cada llamada.

**Entidad set names** (nombres en plural que usa la OData API v9.2):

| Entidad lógica | Entity set (URL) |
|----------------|-----------------|
| `gfit_qlt_ticket` | `gfit_qlt_tickets` |
| `gfit_qlt_ticket_cause` | `gfit_qlt_ticket_causes` |
| `gfit_qlt_ticket_material` | `gfit_qlt_ticket_materials` |
| `gfit_qlt_cause_catalog` | `gfit_qlt_cause_catalogs` |

**Campos clave y mapeos**:

```python
ESTADO_MAP = {
    347780000: 'Pendiente',
    347780001: 'Procesando',
    347780002: 'Finalizada',
}

GRAVEDAD_MAP = {
    347780000: 'Leve',
    347780001: 'Moderada',
    347780002: 'Grave',
}
```

**Métodos públicos**:

| Método | Descripción |
|--------|-------------|
| `get_tickets()` | Lista todas las incidencias (dashboard) |
| `get_ticket_detail(ticket_id)` | Detalle completo: incidencia + causas + materiales agrupados por gravedad. Incluye `conversation_id` y `message_id` |
| `get_ticket_reply_data(ticket_id)` | Devuelve solo `destinatario`, `conversation_id` y `message_id` — datos mínimos para responder por email |
| `get_causes_catalog()` | Catálogo de causas activas ordenadas por `gfit_orden` |
| `update_ticket(ticket_id, datos)` | PATCH genérico sobre un ticket |
| `update_material(material_id, gravedad_str, causa_id)` | Actualiza gravedad y/o causa de un material |
| `create_ticket_cause(ticket_id, nombre, catalog_cause_id)` | Crea una nueva ticket_cause y devuelve su ID |
| `delete_ticket_cause_if_empty(cause_id)` | Elimina la ticket_cause si no le quedan materiales |

**Propiedades de navegación OData** (usan `ID` en mayúsculas, distinto a los campos de filtro):

```python
# Al crear ticket_cause:
'gfit_qlt_ticketID@odata.bind': f'/gfit_qlt_tickets({ticket_id})'
'gfit_qlt_cause_catalogID@odata.bind': f'/gfit_qlt_cause_catalogs({catalog_cause_id})'

# Al actualizar material:
'gfit_qlt_ticket_causeID@odata.bind': f'/gfit_qlt_ticket_causes({causa_id})'
```

> **Nota**: los campos de filtro OData usan minúsculas con prefijo `_` y sufijo `_value` (p. ej. `_gfit_qlt_ticketid_value`), que es distinto del nombre de la propiedad de navegación. No confundirlos.

**SSL**: todas las llamadas usan `verify=False` por el proxy corporativo con inspección SSL. Las advertencias de urllib3 están silenciadas con `urllib3.disable_warnings()`.

### Estructura devuelta por `get_ticket_detail`

```python
{
    'incidencia': {
        'id': '...', 'titulo': '...', 'cliente': '...', 'correo': '...',
        'empresa': '...', 'idioma': '...', 'estado': 'Pendiente', 'fecha': 'YYYY-MM-DD',
        'conversation_id': '...', 'message_id': '...'
    },
    'grupos': [
        {
            'gravedad': 'Grave',  # o 'Moderada' / 'Leve'
            'causas': [
                {
                    'id': '...', 'nombre': '...',
                    'productos': [
                        {
                            'id': '...', 'nombre': '...', 'codigo': '...', 'cantidad': '...',
                            'lote': '...', 'albaran': '...', 'problema': '...',
                            'fecha': 'YYYY-MM-DD', 'gravedad': 'Grave',
                            'causa_nombre': '...', 'causa_id': '...', 'causa_catalog_id': '...'
                        }
                    ]
                }
            ]
        }
    ],
    'all_ticket_causes': {'nombre_causa': 'ticket_cause_id', ...}
}
```

---

## 7. Integración con el endpoint de IA

### Ajuste de tono

El comercial puede reescribir el texto de respuesta al cliente con dos tonos: **amigable** o **formal**.

- **Endpoint interno**: `http://scloudw040:1084/Endpoint_Incidencias/api/incidencias/consulta`
- **Vista Django**: `comercial:ajustar_tono` (POST, AJAX)
- **Timeout**: 120 segundos (la IA puede tardar)

**Payload enviado**:
```json
{
  "texto": "Texto original del comercial",
  "tono": "amigable",
  "cliente": "correo@cliente.com",
  "gravedad": "Grave",
  "causas": [
    {
      "nombre": "Presencia hueso",
      "productos": [
        { "nombre": "Jamón moldeado", "cantidad": "3", "problema": "Descripción del problema" }
      ]
    }
  ]
}
```

**Respuesta esperada**:
```json
{ "content": "Texto reescrito por la IA" }
```

Las causas y productos que se envían se leen dinámicamente de la tabla visible en pantalla (agrupando filas por la causa seleccionada en cada select), no de Dataverse directamente. Así el comercial puede ajustar antes de guardar.

---

## 8. Integración con Power Automate

### Creación de incidencias (portal clientes)

- **Variable de entorno**: `POWER_AUTOMATE_INCIDENCIAS_URL`
- **Vista**: `clientes:nueva_incidencia`
- **Payload enviado**:
```json
{
  "empresa": "Mercadona SA",
  "correo": "cliente@ejemplo.com",
  "conversation_id": "CONV-2026-001",
  "causas": [
    {
      "nombre": "Presencia hueso",
      "productos": [
        {
          "codigo": "LOM-040", "nombre": "Lomo Embuchado 200g",
          "lote": "L2026-07", "cantidad": "50",
          "albaran": "ALB-2026-099", "fecha": "2026-04-01",
          "problema": "Envase roto", "gravedad": "Grave"
        }
      ]
    }
  ]
}
```

Los productos se agrupan por causa antes de enviar. Si `POWER_AUTOMATE_INCIDENCIAS_URL` está vacía, el envío se omite silenciosamente.

---

### Respuesta por email al cliente (portal comercial)

- **Variable de entorno**: `POWER_AUTOMATE_EMAIL_REPLY_URL`
- **Vista**: `comercial:enviar_respuesta` (POST multipart/form-data)
- **Campos del formulario**: `texto` (string) + `adjuntos[]` (archivos, opcional)
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

Los adjuntos se envían con los campos `Name` y `ContentBytes` (base64) directamente en el formato que espera el conector de Office 365 Outlook de Power Automate.

**Restricción**: solo funcionan los tickets que llegaron por email (tienen `gfit_messageid` en Dataverse). Los tickets creados manualmente no tienen `message_id` y la vista devuelve un error descriptivo.

**Flow de Power Automate** (`POWER_AUTOMATE_EMAIL_REPLY_URL`):

| Acción | Detalle |
|--------|---------|
| Trigger HTTP | Recibe el JSON anterior. Trigger público (sin auth Azure AD) |
| Select | Transforma `adjuntos` aplicando `base64ToBinary(item()['ContentBytes'])` a cada elemento |
| Reply to an email (V3) | `Message Id` = `message_id`, `Body` = `cuerpo`, `To` = `destinatario`, `Attachments` = output del Select |
| Response 200 | Confirma a Django que el envío fue correcto |

---

## 9. Autenticación

### Situación actual

Se usa el sistema de autenticación **integrado de Django** (usuario/contraseña en base de datos SQLite). Es temporal y solo para desarrollo.

- El login está en `/login/` (`comercial:login`)
- Las vistas del portal comercial están protegidas con `@login_required`
- El portal de clientes **no requiere login** — es público

### Situación futura

Está previsto sustituirlo por **Microsoft SSO (Azure AD)**. Requiere configuración adicional en el registro de aplicación Azure (distinta a la que ya existe para Dataverse).

Mientras tanto, crear usuarios de prueba con:
```bash
python manage.py createsuperuser
```

---

## 10. Plantillas y frontend

### Herencia de plantillas

```
comercial/base.html  ←  login.html
                     ←  dashboard.html
                     ←  detalle_incidencia.html

clientes/base.html   ←  portal.html
                     ←  nueva_incidencia.html
                     ←  mis_incidencias.html
```

Las plantillas hijas usan `{% extends '...' %}` y rellenan estos bloques:

| Bloque | Uso |
|--------|-----|
| `{% block title %}` | Título de la pestaña del navegador |
| `{% block extra_css %}` | CSS adicional |
| `{% block content %}` | Contenido principal de la página |
| `{% block extra_js %}` | JavaScript adicional |

### Librerías frontend (CDN)

| Librería | Para qué |
|----------|----------|
| Bootstrap 5 | Estilos, grid, componentes (cards, badges, toasts...) |
| Bootstrap Icons | Iconos vectoriales |
| jQuery 3.7.0 | Requerido por DataTables |
| DataTables 1.13.6 | Tabla interactiva con paginación, búsqueda y filtros |

### DataTables — configuración del dashboard

```javascript
tabla = $('#tabla-incidencias').DataTable({
    language: { url: '...es-ES.json' },
    pageLength: 10,
    order: [[3, 'desc']],
    columnDefs: [{ orderable: false, targets: [2, 4] }],
    info: false,
});
```

Los filtros (por estado y por calidad) se implementan con `$.fn.dataTable.ext.search` usando atributos `data-estado` y `data-calidad` en las filas `<tr>`.

### JavaScript en `detalle_incidencia.html`

Variables globales inyectadas desde Django:

| Variable JS | Origen | Contenido |
|-------------|--------|-----------|
| `CAUSAS_CATALOGO` | `causas_catalogo_json` | Array de `{id, nombre, gravedad}` del catálogo activo |
| `CAUSA_ID_MAP` | `causa_id_map_json` | Objeto `{nombre_causa: ticket_cause_id}` de todas las causas del ticket |

Funciones principales:

- **`guardarGravedadesGrupo(gravedad)`**: recoge los cambios de gravedad y causa de todas las filas del grupo, los envía a `/incidencia/<id>/gravedades/` y recarga la página si tiene éxito
- **`ajustarTono(tono, gravedad)`**: agrupa las filas del grupo por causa seleccionada, envía el texto y contexto al endpoint de IA, actualiza el textarea con la respuesta
- **`derivarCalidad()`**: llama a `/incidencia/<id>/derivar-calidad/` (pendiente de implementación real)
- **`colorearGravedad(el)`**: aplica clase CSS (`gravedad-grave`, `gravedad-moderada`, `gravedad-leve`) al select de gravedad
- **`agregarAdjuntos(gravedadId)`**: añade los archivos seleccionados al array `archivosAcumulados[gravedadId]` sin reemplazar los anteriores; resetea el input para permitir volver a seleccionar
- **`renderizarAdjuntos(gravedadId)`**: dibuja los archivos acumulados como badges con botón × para eliminar individualmente
- **`eliminarAdjunto(gravedadId, idx)`**: elimina un archivo del array acumulado por índice y re-renderiza
- **`enviarRespuesta(gravedad)`**: envía el texto del textarea y todos los archivos acumulados via `multipart/form-data` a `/incidencia/<id>/enviar-respuesta/`; vacía la lista de adjuntos y muestra alerta de éxito o error

**Variable global `archivosAcumulados`**: objeto JS `{ gravedadId: [File, ...] }` que mantiene los archivos añadidos por el usuario para cada grupo antes de enviar. Se limpia tras un envío exitoso.

Preselección de causa: se hace por **ID del catálogo** (`data-causa-catalog-id`) y usa el nombre como fallback. Esto garantiza la selección correcta aunque el `gfit_name` de la ticket_cause no coincida exactamente con `gfit_nombrecausa` del catálogo.

---

## 11. Flujo de una petición HTTP

### Comercial abre el detalle de una incidencia

```
GET /incidencia/<guid>/
  → detalle_incidencia()
      → DataverseClient().get_ticket_detail(id)
          → GET gfit_qlt_tickets(<id>)
          → GET gfit_qlt_ticket_causes?$filter=_gfit_qlt_ticketid_value eq <id>
          → por cada causa: GET gfit_qlt_ticket_materials?$filter=_gfit_qlt_ticket_causeid_value eq <cause_id>
      → DataverseClient().get_causes_catalog()
          → GET gfit_qlt_cause_catalogs?$filter=gfit_activo eq true
      → render('detalle_incidencia.html', {incidencia, grupos, causas_catalogo_json, causa_id_map_json})
```

### Comercial guarda cambios de gravedad/causa

```
POST /incidencia/<guid>/gravedades/  (AJAX, JSON)
  → actualizar_gravedades()
      → por cada producto:
          → [si causa nueva] DataverseClient().create_ticket_cause(ticket_id, nombre, catalog_id)
              → POST gfit_qlt_ticket_causes  (con @odata.bind al ticket y al catálogo)
          → DataverseClient().update_material(material_id, gravedad, causa_id)
              → PATCH gfit_qlt_ticket_materials(<id>)  {gfit_gravedad, gfit_qlt_ticket_causeID@odata.bind}
          → [si cambió causa] DataverseClient().delete_ticket_cause_if_empty(causa_id_original)
              → GET gfit_qlt_ticket_materials?$top=1&$filter=_gfit_qlt_ticket_causeid_value eq <id>
              → [si vacía] DELETE gfit_qlt_ticket_causes(<id>)
  → JsonResponse({'ok': True})
  → JS recarga la página
```

### Comercial ajusta el tono con IA

```
POST /ajustar-tono/  (AJAX, JSON)
  → ajustar_tono()
      → POST http://scloudw040:1084/Endpoint_Incidencias/api/incidencias/consulta
          → {texto, tono, cliente, gravedad, causas: [{nombre, productos: [{nombre, cantidad, problema}]}]}
      → JsonResponse({'texto': datos['content']})
  → JS actualiza el textarea sin recargar la página
```

### Comercial envía la respuesta por email

```
POST /incidencia/<guid>/enviar-respuesta/  (multipart/form-data)
  → enviar_respuesta()
      → valida que 'texto' no esté vacío
      → DataverseClient().get_ticket_reply_data(incidencia_id)
          → GET gfit_qlt_tickets(<id>)?$select=gfit_correocliente,gfit_conversationid,gfit_messageid
      → valida que message_id no esté vacío (tickets sin email de origen no soportados)
      → codifica adjuntos recibidos en base64 {Name, ContentBytes}
      → POST POWER_AUTOMATE_EMAIL_REPLY_URL
          → {destinatario, conversation_id, message_id, cuerpo, adjuntos:[{Name, ContentBytes}]}
      → JsonResponse({'ok': True})
  → JS limpia lista de adjuntos y muestra alerta de éxito
```

### Cliente envía una incidencia

```
POST /clientes/nueva-incidencia/
  → nueva_incidencia()
      → valida empresa, correo, conversation_id y que haya al menos un producto
      → agrupa productos por causa
      → POST POWER_AUTOMATE_INCIDENCIAS_URL (json=payload)
      → render('nueva_incidencia.html', {'enviado': True})
```

---

## 12. Variables de entorno

Almacenadas en `.env` en la raíz del proyecto. **No se suben a git**.

| Variable | Descripción |
|----------|-------------|
| `AZURE_CLIENT_ID` | Client ID del registro de aplicación Azure |
| `AZURE_CLIENT_SECRET` | Secret del registro de aplicación Azure |
| `AZURE_TENANT_ID` | Tenant ID de la organización Azure |
| `DATAVERSE_URL` | URL base de la organización Dataverse (ej. `https://gf-it-dev.crm4.dynamics.com`) |
| `POWER_AUTOMATE_INCIDENCIAS_URL` | URL del flujo de Power Automate para creación de incidencias (portal clientes) |
| `POWER_AUTOMATE_EMAIL_REPLY_URL` | URL del flujo de Power Automate para responder por email al cliente (portal comercial). El trigger debe ser público (sin auth Azure AD) |

---

## 13. Comandos de desarrollo

```bash
# Activar el entorno virtual (necesario siempre)
venv\Scripts\activate          # Windows PowerShell
source venv/bin/activate        # Linux/Mac

# Arrancar el servidor de desarrollo
python manage.py runserver

# Actualizar requirements.txt tras instalar nuevas librerías
venv\Scripts\pip freeze > requirements.txt

# Crear un usuario de prueba para el portal comercial
python manage.py createsuperuser

# Git — operaciones habituales
git status
git add <fichero>
git commit -m "mensaje"
git push -u origin <rama>
```

---

## 14. Dependencias

Definidas en `requirements.txt`. Las principales:

| Paquete | Para qué |
|---------|----------|
| `django` | Framework web principal |
| `python-dotenv` | Cargar variables de entorno desde `.env` |
| `requests` | Llamadas HTTP a Dataverse, endpoint IA y Power Automate |
| `urllib3` | Control de warnings SSL (`verify=False`) |
| `msal` | Autenticación Microsoft Azure AD (client credentials flow) |

---

## 15. Pendiente de implementar

| Funcionalidad | Bloqueado por | Dónde implementar |
|---------------|--------------|-------------------|
| Login con Microsoft SSO | Configuración Azure AD (distinta a la de Dataverse) | `comercial/views.py`, `settings.py` |
| Derivar a Calidad (guardar en Dataverse) | Definir campo en Dataverse | `DataverseClient` + `comercial/views.py:derivar_calidad` |
| Marcar incidencia como Finalizada | Pendiente de diseño | `comercial/views.py` + nuevo endpoint |
| Enviar email desde ticket sin `message_id` | Tickets creados manualmente no tienen hilo de email origen | Habría que crear un email nuevo en lugar de reply |
| Adaptación responsive móvil/tablet | — | Templates CSS |
