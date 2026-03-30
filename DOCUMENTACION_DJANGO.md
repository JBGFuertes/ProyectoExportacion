# Documentación técnica — EProveedor Django

> Este documento explica la estructura y los conceptos de Django aplicados en este proyecto. No entra en detalle sobre la funcionalidad de negocio, sino que sirve como referencia para entender cómo está organizado el código y qué papel cumple cada pieza desde el punto de vista del framework.

---

## Índice

1. [¿Qué es Django?](#1-qué-es-django)
2. [Estructura del proyecto](#2-estructura-del-proyecto)
3. [Configuración (`config/`)](#3-configuración-config)
4. [La aplicación `core`](#4-la-aplicación-core)
5. [Modelos](#5-modelos)
6. [Vistas (`views.py`)](#6-vistas-viewspy)
7. [URLs (`urls.py`)](#7-urls-urlspy)
8. [Plantillas (templates)](#8-plantillas-templates)
9. [Archivos estáticos](#9-archivos-estáticos)
10. [Middleware](#10-middleware)
11. [Context processors](#11-context-processors)
12. [Template tags personalizados](#12-template-tags-personalizados)
13. [Sesiones](#13-sesiones)
14. [Cliente API externo (`core/api/`)](#14-cliente-api-externo-coreapi)
15. [Flujo de una petición HTTP](#15-flujo-de-una-petición-http)
16. [Dependencias](#16-dependencias)

---

## 1. ¿Qué es Django?

Django es un framework web Python que sigue el patrón **MTV** (Model–Template–View), análogo al clásico MVC:

| Capa | En Django | Responsabilidad |
|------|-----------|-----------------|
| Model | `models.py` | Define la estructura de datos y la lógica de acceso a base de datos |
| Template | archivos `.html` en `templates/` | Define cómo se presenta la información al usuario |
| View | `views.py` | Recibe la petición HTTP, obtiene datos y devuelve una respuesta |

Django también incluye de serie: sistema de routing de URLs, motor de plantillas, ORM para bases de datos, sistema de sesiones, middleware y un panel de administración.

---

## 2. Estructura del proyecto

Un proyecto Django se compone de un **proyecto** (configuración global) y una o varias **aplicaciones** (módulos de funcionalidad). En este caso:

```
EProveedor_Django/
│
├── manage.py               # Punto de entrada para comandos Django (runserver, migrate, etc.)
│
├── config/                 # Configuración global del PROYECTO Django
│   ├── settings.py         # Ajustes principales (base de datos, apps, middleware…)
│   ├── urls.py             # Router principal de URLs
│   ├── wsgi.py             # Interfaz WSGI para producción
│   └── asgi.py             # Interfaz ASGI (async, opcional)
│
├── core/                   # La única APLICACIÓN Django del proyecto
│   ├── apps.py             # Registro de la aplicación
│   ├── models.py           # Modelos ORM (vacío en este proyecto)
│   ├── views.py            # Lógica de negocio y respuestas HTTP
│   ├── urls.py             # URLs propias de la app
│   ├── admin.py            # Registro en el panel de administración
│   ├── middleware.py       # Middleware personalizado
│   ├── context_processors.py  # Datos globales inyectados en todas las plantillas
│   ├── templatetags/       # Filtros y tags de plantilla personalizados
│   ├── api/                # Cliente HTTP para la API externa
│   ├── templates/          # Plantillas HTML
│   ├── static/             # CSS, imágenes propias de la app
│   └── migrations/         # Historial de cambios en base de datos
│
├── requirements.txt        # Dependencias Python del proyecto
├── db.sqlite3              # Base de datos SQLite (solo sesiones en este proyecto)
└── staticfiles/            # Archivos estáticos recopilados para producción
```

### `manage.py`

Script que Django genera automáticamente. Permite ejecutar comandos de gestión:

```bash
python manage.py runserver       # Arranca el servidor de desarrollo
python manage.py migrate         # Aplica migraciones a la base de datos
python manage.py collectstatic   # Recopila archivos estáticos en STATIC_ROOT
python manage.py createsuperuser # Crea un usuario administrador
```

---

## 3. Configuración (`config/`)

### `settings.py`

Fichero central de configuración. Los ajustes más relevantes de este proyecto:

```python
# Aplicaciones instaladas — Django carga solo las que estén aquí
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.sessions',   # Sistema de sesiones
    'django.contrib.staticfiles',
    'core',                      # Nuestra aplicación
]

# Middleware activo (se ejecutan en orden en cada petición)
MIDDLEWARE = [
    'whitenoise.middleware.WhiteNoiseMiddleware',   # Sirve estáticos en producción
    ...
    'core.middleware.AuthRequiredMiddleware',       # Middleware personalizado de autenticación
]

# Base de datos — SQLite para este proyecto (solo almacena sesiones)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Context processors — funciones que inyectan datos en TODAS las plantillas
TEMPLATES = [{
    'OPTIONS': {
        'context_processors': [
            ...
            'core.context_processors.menu_processor',  # Menú y datos de usuario
        ]
    }
}]

# URL base de la API externa
API_BASE_URL = 'http://10.92.0.40:1082/eproveedorAPI'

# Archivos estáticos
STATIC_URL = '/eproveedor_2/static/'
STATIC_ROOT = BASE_DIR / 'static'
```

### `urls.py` (raíz del proyecto)

Define el router principal. Delega todas las rutas de la aplicación al módulo `core.urls`:

```python
urlpatterns = [
    path('eproveedor_2/admin/', admin.site.urls),
    path('eproveedor_2/', include('core.urls')),   # Todas las URLs van a core
]
```

---

## 4. La aplicación `core`

En Django, una **aplicación** es un módulo Python reutilizable con su propia lógica, modelos, vistas y plantillas. Este proyecto tiene una sola aplicación: `core`.

### `apps.py`

Registro mínimo que Django requiere para reconocer la aplicación:

```python
class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
```

Se activa incluyendo `'core'` en `INSTALLED_APPS` del `settings.py`.

### `migrations/`

Carpeta donde Django guarda el historial de cambios en los modelos de base de datos. Como en este proyecto no se usan modelos ORM, la carpeta está vacía (solo contiene `__init__.py`).

---

## 5. Modelos

En Django, los **modelos** (`models.py`) son clases Python que mapean directamente a tablas de base de datos a través del ORM (Object-Relational Mapper).

**En este proyecto, `models.py` está vacío.** No se usa el ORM de Django para almacenar datos de negocio. Toda la información viene de una API externa. La base de datos SQLite solo almacena **sesiones de usuario** (gestionadas automáticamente por Django).

> Esta es una arquitectura válida cuando Django actúa como capa de presentación ("frontend") que consume servicios externos, sin necesitar persistencia propia.

---

## 6. Vistas (`views.py`)

Las **vistas** son funciones (o clases) Python que:
1. Reciben un objeto `HttpRequest` con la información de la petición
2. Realizan la lógica necesaria (llamar a la API, procesar datos…)
3. Devuelven un objeto `HttpResponse` (HTML renderizado, JSON, archivo, redirección…)

Este proyecto usa **vistas basadas en funciones** (FBV — Function-Based Views). Ejemplo de patrón habitual:

```python
def pedidos_view(request):
    # 1. Comprobar acceso mediante el menú de la sesión
    if not check_page_access(request, 'Pedidos'):
        return redirect('inicio')

    # 2. Obtener datos de la API externa
    api = ApiClient(base_url=settings.API_BASE_URL, token=request.session['access_token'])
    response = api.compras__pedidos(...)

    # 3. Renderizar plantilla con contexto
    return render(request, 'core/pages/pedidos.html', {
        'pedidos': response['data'],
        'section_pages': get_section_pages(request, 'Compras'),
    })
```

Existen dos tipos de vistas en este proyecto:

| Tipo | Descripción | Respuesta |
|------|-------------|-----------|
| **Vistas de página** | Renderizan una plantilla HTML completa | `render(request, 'template.html', context)` |
| **Vistas AJAX** | Devuelven datos JSON para peticiones del frontend | `JsonResponse({...})` |

---

## 7. URLs (`urls.py`)

Django usa un sistema de **routing de URLs** declarativo. Cada URL se asocia a una vista mediante la función `path()` o `re_path()`.

### Estructura de URLs en este proyecto

El fichero raíz (`config/urls.py`) delega en `core/urls.py`, que contiene ~70 rutas organizadas por sección:

```python
# core/urls.py
urlpatterns = [
    # Autenticación
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Selección de empresa/proveedor
    path('seleccionar-empresa/', views.seleccionar_empresa_view, name='seleccionar_empresa'),

    # Páginas de la aplicación
    path('compras/pedidos/', views.pedidos_view, name='pedidos'),
    path('contabilidad/facturas/', views.facturas_view, name='facturas'),

    # Endpoints AJAX (retornan JSON)
    path('api/obtener-pedidos/', views.obtener_pedidos_ajax, name='obtener_pedidos_ajax'),
    path('api/descargar-factura/', views.descargar_factura_ajax, name='descargar_factura_ajax'),
    ...
]
```

El parámetro `name` permite referenciar URLs en plantillas y código Python sin hardcodear la ruta:

```html
<!-- En plantillas -->
<a href="{% url 'pedidos' %}">Ver Pedidos</a>
```

```python
# En vistas
from django.shortcuts import redirect
return redirect('login')
```

---

## 8. Plantillas (templates)

Django incluye un **motor de plantillas** propio. Las plantillas son ficheros HTML con sintaxis especial:

| Sintaxis | Uso |
|----------|-----|
| `{{ variable }}` | Mostrar el valor de una variable del contexto |
| `{% tag %}` | Lógica de control: `{% if %}`, `{% for %}`, `{% block %}`, `{% url %}`, etc. |
| `{% load %}` | Cargar librerías de tags/filtros (ej. `{% load core_tags %}`) |
| `{{ var\|filtro }}` | Aplicar un filtro a una variable (ej. `{{ nombre\|upper }}`) |

### Estructura de plantillas

```
core/templates/core/
│
├── base.html                   # Plantilla base — estructura HTML completa (sidebar, navbar…)
│
├── sections/                   # Sub-bases por sección (heredan de base.html)
│   ├── compras_base.html
│   ├── contabilidad_base.html
│   └── ...
│
└── pages/                      # Plantillas de página (heredan de su sección)
    ├── login.html
    ├── pedidos.html
    ├── facturas.html
    └── ...
```

### Herencia de plantillas

Django permite que una plantilla **herede** de otra con `{% extends %}` y defina bloques con `{% block %}`:

```html
<!-- base.html — define la estructura general -->
<html>
  <body>
    <nav>...</nav>       <!-- Sidebar con menú dinámico -->
    {% block content %}
      <!-- Las páginas hijas reemplazan este bloque -->
    {% endblock %}
  </body>
</html>
```

```html
<!-- pages/pedidos.html — hereda de la base de su sección -->
{% extends "core/sections/compras_base.html" %}

{% block content %}
  <h1>Pedidos</h1>
  <!-- Contenido específico de esta página -->
{% endblock %}
```

Este patrón evita duplicar el HTML del layout en cada página.

---

## 9. Archivos estáticos

Django separa los **archivos estáticos** (CSS, JS, imágenes) de la lógica Python.

### En desarrollo

Los archivos en `core/static/` son servidos automáticamente por Django cuando `DEBUG=True`.

```
core/static/core/
├── css/custom.css
└── img/
    ├── logo-grupo-blanco-negro.png
    └── login-bg.jpg
```

Se referencian en plantillas con:

```html
{% load static %}
<link rel="stylesheet" href="{% static 'core/css/custom.css' %}">
<img src="{% static 'core/img/logo-grupo-blanco-negro.png' %}">
```

### En producción

Se usa el comando `python manage.py collectstatic` para copiar todos los estáticos a `STATIC_ROOT`. Luego **WhiteNoise** los sirve directamente desde el proceso Python sin necesidad de Nginx/Apache para los estáticos:

```python
# settings.py
MIDDLEWARE = [
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Debe ir al principio
    ...
]
```

---

## 10. Middleware

El **middleware** es una capa de procesamiento que se ejecuta en cada petición HTTP, **antes** de que llegue a la vista y **después** de que la vista genere la respuesta.

```
Petición HTTP
     ↓
[Middleware 1]  ←→  [Middleware 2]  ←→  ... ←→  [Vista]
     ↑
Respuesta HTTP
```

Django incluye varios middlewares de serie (seguridad, sesiones, autenticación). Este proyecto añade uno personalizado:

### `AuthRequiredMiddleware` (`core/middleware.py`)

Intercepta **todas** las peticiones y:

1. Deja pasar sin restricciones: `/login/`, `/logout/`, rutas de estáticos
2. Para el resto, comprueba si hay `access_token` válido en sesión
3. Si el token está a punto de expirar, intenta refrescarlo llamando a la API
4. Si no hay sesión válida:
   - **Petición normal**: redirige al login
   - **Petición AJAX**: devuelve `{"error": "..."}` con código HTTP 401

```python
class AuthRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response      # Referencia al siguiente middleware/vista

    def __call__(self, request):
        # Lógica ANTES de la vista
        if not autenticado(request):
            return redirect('login')

        response = self.get_response(request) # Llamar a la vista

        # Lógica DESPUÉS de la vista (si fuera necesario)
        return response
```

Se activa añadiéndolo a `MIDDLEWARE` en `settings.py`.

---

## 11. Context processors

Un **context processor** es una función que Django llama automáticamente en cada petición y cuyo valor de retorno se inyecta en el contexto de **todas** las plantillas.

Son útiles para datos que necesitan estar disponibles en toda la aplicación (menú de navegación, datos del usuario en sesión, configuración global…).

### `menu_processor` (`core/context_processors.py`)

```python
def menu_processor(request):
    # Extrae el menú almacenado en sesión y lo estructura
    menu_data = process_menu_web(request.session.get('menu_web', []))
    datos_usuario = request.session.get('datosUsuario', {})

    return {
        'menu_data': menu_data,       # Disponible en cualquier plantilla como {{ menu_data }}
        'datosUsuario': datos_usuario # Disponible como {{ datosUsuario }}
    }
```

Se registra en `settings.py`:

```python
TEMPLATES = [{
    'OPTIONS': {
        'context_processors': [
            ...
            'core.context_processors.menu_processor',
        ]
    }
}]
```

---

## 12. Template tags personalizados

Django permite extender su motor de plantillas con **filtros** y **tags** propios, que se agrupan en módulos Python dentro de `templatetags/`.

### `core/templatetags/core_tags.py`

Contiene el filtro `normalize_section_name`, usado en plantillas para convertir nombres de sección en identificadores CSS válidos:

```python
# core/templatetags/core_tags.py
from django import template
register = template.Library()

@register.filter
def normalize_section_name(value):
    """'Mis Datos' → 'misdatos'"""
    ...
```

Uso en plantilla:

```html
{% load core_tags %}
<div id="section-{{ seccion|normalize_section_name }}">
```

---

## 13. Sesiones

Django incluye un **sistema de sesiones** que permite almacenar datos del usuario entre peticiones (HTTP es sin estado por definición).

Por defecto, los datos de sesión se guardan en la base de datos (tabla `django_session` de SQLite) y el navegador recibe solo un identificador de sesión en una cookie.

En este proyecto, la sesión almacena:

| Clave | Contenido |
|-------|-----------|
| `access_token` | JWT para autenticarse contra la API externa |
| `refresh_token` | JWT para renovar el `access_token` |
| `datosUsuario` | Datos básicos del usuario (nombre, código proveedor) |
| `menu_web` | Estructura de menú devuelta por la API |
| `empresa_seleccionada` | Empresa activa en el contexto multi-empresa |

Acceso desde cualquier vista:

```python
def mi_vista(request):
    token = request.session['access_token']
    request.session['empresa_seleccionada'] = nueva_empresa
    request.session.flush()  # Destruir sesión completa (logout)
```

---

## 14. Cliente API externo (`core/api/`)

Este proyecto no tiene modelos ORM propios. Toda la lógica de datos está en una **API REST externa**. El directorio `core/api/` contiene el cliente para comunicarse con ella.

```
core/api/
├── __init__.py    # Exporta ApiClient y todos los modelos
├── client.py      # Clase ApiClient — wrapper de requests HTTP
└── models.py      # Dataclasses Python que representan los payloads de la API
```

> Nota: `client.py` y `models.py` son **auto-generados** a partir del fichero `swagger.json` mediante el script `generate_api_client.py`. No deben editarse manualmente.

### `ApiClient` (`core/api/client.py`)

```python
class ApiClient:
    def __init__(self, base_url, token=None):
        self.base_url = base_url
        self.token = token

    def _request(self, method, endpoint, **kwargs):
        headers = {'Authorization': f'Bearer {self.token}'}
        response = requests.request(method, url, headers=headers, verify=False)
        return {'status_code': response.status_code, 'data': response.json(), 'success': response.ok}

    def compras__pedidos(self, ...):
        return self._request('GET', '/Compras/Pedidos', ...)
```

Uso típico desde una vista:

```python
api = ApiClient(base_url=settings.API_BASE_URL, token=request.session['access_token'])
result = api.compras__pedidos(codigoProv='...', fecha='...')
if result['success']:
    pedidos = result['data']
```

---

## 15. Flujo de una petición HTTP

Ejemplo completo del ciclo de vida de una petición a `/eproveedor_2/compras/pedidos/`:

```
Navegador
    │
    │  GET /eproveedor_2/compras/pedidos/
    ▼
Django (config/urls.py)
    │  → incluye core.urls
    ▼
core/urls.py
    │  → path('compras/pedidos/', views.pedidos_view)
    ▼
Middleware stack (en orden)
    │  1. WhiteNoiseMiddleware     → no es estático, continúa
    │  2. SessionMiddleware        → carga sesión del usuario
    │  3. AuthRequiredMiddleware   → comprueba token, refresca si hace falta
    ▼
views.pedidos_view(request)
    │  1. check_page_access()      → ¿tiene permiso según menú en sesión?
    │  2. ApiClient(token=...)     → instancia cliente API
    │  3. api.compras__pedidos()   → llamada HTTP a la API externa
    │  4. render(request, 'core/pages/pedidos.html', contexto)
    ▼
Motor de plantillas Django
    │  1. Carga context_processors → menu_processor() inyecta menú y usuario
    │  2. Renderiza pedidos.html   → extiende compras_base.html → extiende base.html
    ▼
HttpResponse (HTML generado)
    │
    ▼
Navegador
```

---

## 16. Dependencias

Definidas en `requirements.txt`:

| Paquete | Versión | Propósito |
|---------|---------|-----------|
| `Django` | >=5.1 | Framework web principal |
| `requests` | >=2.31.0 | Cliente HTTP para llamar a la API externa |
| `XlsxWriter` | >=3.2.0 | Generación de ficheros Excel en las exportaciones |
| `whitenoise` | >=6.6.0 | Servicio de archivos estáticos en producción |

Instalación:

```bash
python -m venv env
source env/bin/activate   # Linux/Mac
env\Scripts\activate      # Windows

pip install -r requirements.txt
```

---

*Documentación generada para el proyecto EProveedor Django — estructura y conceptos Django.*
