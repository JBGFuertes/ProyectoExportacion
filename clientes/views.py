import json
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from django.conf import settings
from django.shortcuts import render
from django.contrib import messages


# Incidencias mock para simular la consulta por email
INCIDENCIAS_CLIENTE_MOCK = [
    {'referencia': 'INC-2026-001', 'titulo': 'Producto dañado en envío', 'estado': 'Pendiente', 'fecha': '2026-03-25', 'correo': 'garcia@ejemplo.com'},
    {'referencia': 'INC-2026-003', 'titulo': 'Lote incorrecto recibido', 'estado': 'Pendiente', 'fecha': '2026-03-27', 'correo': 'garcia@ejemplo.com'},
    {'referencia': 'INC-2026-002', 'titulo': 'Error en cantidad facturada', 'estado': 'Procesando', 'fecha': '2026-03-26', 'correo': 'martin@ejemplo.com'},
    {'referencia': 'INC-2026-004', 'titulo': 'Retraso en entrega', 'estado': 'Finalizada', 'fecha': '2026-03-10', 'correo': 'lopez@ejemplo.com'},
    {'referencia': 'INC-2026-005', 'titulo': 'Envase roto en recepción', 'estado': 'Pendiente', 'fecha': '2026-03-28', 'correo': 'jose.barazanavarro@grupofuertes.com'},
    {'referencia': 'INC-2026-006', 'titulo': 'Lote incorrecto en pedido', 'estado': 'Procesando', 'fecha': '2026-03-27', 'correo': 'jose.barazanavarro@grupofuertes.com'},
    {'referencia': 'INC-2026-007', 'titulo': 'Cantidad facturada no coincide', 'estado': 'Pendiente', 'fecha': '2026-03-29', 'correo': 'jose.barazanavarro@grupofuertes.com'},
    {'referencia': 'INC-2026-008', 'titulo': 'Producto caducado recibido', 'estado': 'Finalizada', 'fecha': '2026-03-15', 'correo': 'jose.barazanavarro@grupofuertes.com'},
]


def portal(request):
    """Página de entrada del portal de clientes."""
    return render(request, 'clientes/portal.html')


def _leer_productos_url(request):
    """Lee productos prefijados por URL (?p0_codigo=X&p0_nombre=Y...)"""
    productos = []
    i = 0
    while f'p{i}_codigo' in request.GET or f'p{i}_nombre' in request.GET:
        productos.append({
            'codigo': request.GET.get(f'p{i}_codigo', ''),
            'nombre': request.GET.get(f'p{i}_nombre', ''),
            'lote': request.GET.get(f'p{i}_lote', ''),
            'cantidad': request.GET.get(f'p{i}_cantidad', ''),
            'albaran': request.GET.get(f'p{i}_albaran', ''),
            'fecha': request.GET.get(f'p{i}_fecha', ''),
            'problema': request.GET.get(f'p{i}_problema', ''),
        })
        i += 1
    return productos


def _leer_productos_post(request):
    """Reconstruye la lista de productos desde el POST."""
    productos = []
    i = 0
    while f'p{i}_codigo' in request.POST or f'p{i}_nombre' in request.POST:
        productos.append({
            'codigo': request.POST.get(f'p{i}_codigo', '').strip(),
            'nombre': request.POST.get(f'p{i}_nombre', '').strip(),
            'lote': request.POST.get(f'p{i}_lote', '').strip(),
            'cantidad': request.POST.get(f'p{i}_cantidad', '').strip(),
            'albaran': request.POST.get(f'p{i}_albaran', '').strip(),
            'fecha': request.POST.get(f'p{i}_fecha', '').strip(),
            'problema': request.POST.get(f'p{i}_problema', '').strip(),
        })
        i += 1
    return productos


def nueva_incidencia(request):
    """Formulario para que el cliente registre una nueva incidencia."""
    if request.method == 'POST':
        identificacion = {
            'empresa': request.POST.get('empresa', '').strip(),
            'correo': request.POST.get('correo', '').strip(),
            'conversation_id': request.POST.get('conversation_id', '').strip(),
        }
        productos = _leer_productos_post(request)

        # Validación
        if not all(identificacion.values()):
            messages.error(request, 'Los campos Empresa, Correo y ConversationID son obligatorios.')
            return render(request, 'clientes/nueva_incidencia.html', {
                'identificacion': identificacion,
                'productos': productos,
            })

        if not productos:
            messages.error(request, 'Añade al menos un producto.')
            return render(request, 'clientes/nueva_incidencia.html', {
                'identificacion': identificacion,
                'productos': productos,
            })

        payload = {**identificacion, 'productos': productos}

        url = settings.POWER_AUTOMATE_INCIDENCIAS_URL
        if url:
            try:
                requests.post(url, json=payload, timeout=15, verify=False)
            except Exception:
                pass

        return render(request, 'clientes/nueva_incidencia.html', {'enviado': True})

    # GET: leer prefill de URL
    identificacion = {
        'empresa': request.GET.get('empresa', ''),
        'correo': request.GET.get('correo', ''),
        'conversation_id': request.GET.get('conv', ''),
    }
    productos = _leer_productos_url(request) or [{}]

    return render(request, 'clientes/nueva_incidencia.html', {
        'identificacion': identificacion,
        'productos': productos,
    })


def mis_incidencias(request):
    """El cliente consulta sus incidencias introduciendo su email."""
    incidencias = None
    email_buscado = ''

    if request.method == 'POST':
        email_buscado = request.POST.get('correo', '').strip().lower()
        if email_buscado:
            # Con Dataverse real: filtrar por correo en la API
            # Por ahora usamos datos mock
            incidencias = [i for i in INCIDENCIAS_CLIENTE_MOCK if i['correo'].lower() == email_buscado]
            if not incidencias:
                messages.warning(request, 'No encontramos incidencias asociadas a ese correo.')
        else:
            messages.error(request, 'Introduce un correo válido.')

    return render(request, 'clientes/mis_incidencias.html', {
        'incidencias': incidencias,
        'email_buscado': email_buscado,
    })
