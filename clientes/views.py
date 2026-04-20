import json
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from django.conf import settings
from django.shortcuts import render
from django.contrib import messages
from comercial.api.dataverse import DataverseClient


def portal(request):
    """Página de entrada del portal de clientes."""
    return render(request, 'clientes/portal.html')


def _leer_productos_url(request):
    """Lee productos prefijados por URL (?p0_codigo=X&p0_nombre=Y...)"""
    productos = []
    i = 0
    while f'p{i}_codigo' in request.GET or f'p{i}_nombre' in request.GET:
        productos.append({
            'codigo':   request.GET.get(f'p{i}_codigo', ''),
            'nombre':   request.GET.get(f'p{i}_nombre', ''),
            'lote':     request.GET.get(f'p{i}_lote', ''),
            'cantidad': request.GET.get(f'p{i}_cantidad', ''),
            'albaran':  request.GET.get(f'p{i}_albaran', ''),
            'fecha':    request.GET.get(f'p{i}_fecha', ''),
            'problema': request.GET.get(f'p{i}_problema', ''),
            'causa':    request.GET.get(f'p{i}_causa', ''),
            'gravedad': request.GET.get(f'p{i}_gravedad', ''),
        })
        i += 1
    return productos


def _leer_productos_post(request):
    """Reconstruye la lista de productos desde el POST."""
    productos = []
    i = 0
    while f'p{i}_codigo' in request.POST or f'p{i}_nombre' in request.POST:
        productos.append({
            'codigo':   request.POST.get(f'p{i}_codigo', '').strip(),
            'nombre':   request.POST.get(f'p{i}_nombre', '').strip(),
            'lote':     request.POST.get(f'p{i}_lote', '').strip(),
            'cantidad': request.POST.get(f'p{i}_cantidad', '').strip(),
            'albaran':  request.POST.get(f'p{i}_albaran', '').strip(),
            'fecha':    request.POST.get(f'p{i}_fecha', '').strip(),
            'problema': request.POST.get(f'p{i}_problema', '').strip(),
            'causa':    request.POST.get(f'p{i}_causa', '').strip(),
            'gravedad': request.POST.get(f'p{i}_gravedad', '').strip(),
        })
        i += 1
    return productos


def nueva_incidencia(request):
    """Formulario para que el cliente registre una nueva incidencia."""
    if request.method == 'POST':
        identificacion = {
            'empresa':         request.POST.get('empresa', '').strip(),
            'correo':          request.POST.get('correo', '').strip(),
            'conversation_id': request.POST.get('conversation_id', '').strip(),
        }
        productos = _leer_productos_post(request)

        try:
            causas_catalogo = DataverseClient().get_causes_catalog()
        except Exception:
            causas_catalogo = []
        catalogo_ctx = {
            'causas_catalogo':      causas_catalogo,
            'causas_catalogo_json': json.dumps(causas_catalogo, ensure_ascii=False),
        }

        if not all(identificacion.values()):
            messages.error(request, 'Los campos Empresa, Correo y ConversationID son obligatorios.')
            return render(request, 'clientes/nueva_incidencia.html', {
                'identificacion': identificacion,
                'productos':      productos,
                **catalogo_ctx,
            })

        if not productos:
            messages.error(request, 'Añade al menos un producto.')
            return render(request, 'clientes/nueva_incidencia.html', {
                'identificacion': identificacion,
                'productos':      productos,
                **catalogo_ctx,
            })

        # Agrupar productos por causa; gravedad va dentro de cada producto
        causas_agrupadas = {}
        for p in productos:
            clave = p['causa']
            if clave not in causas_agrupadas:
                causas_agrupadas[clave] = {'nombre': p['causa'], 'productos': []}
            causas_agrupadas[clave]['productos'].append({
                k: v for k, v in p.items() if k != 'causa'
            })

        payload = {
            **identificacion,
            'causas': list(causas_agrupadas.values()),
        }

        url = settings.POWER_AUTOMATE_INCIDENCIAS_URL
        if url:
            try:
                requests.post(url, json=payload, timeout=15, verify=False)
            except Exception:
                pass

        return render(request, 'clientes/nueva_incidencia.html', {'enviado': True})

    # GET: leer prefill de URL
    identificacion = {
        'empresa':         request.GET.get('empresa', ''),
        'correo':          request.GET.get('correo', ''),
        'conversation_id': request.GET.get('conv', ''),
    }
    productos = _leer_productos_url(request) or [{}]

    try:
        causas_catalogo = DataverseClient().get_causes_catalog()
    except Exception:
        causas_catalogo = []

    return render(request, 'clientes/nueva_incidencia.html', {
        'identificacion':      identificacion,
        'productos':           productos,
        'causas_catalogo':     causas_catalogo,
        'causas_catalogo_json': json.dumps(causas_catalogo, ensure_ascii=False),
    })


def mis_incidencias(request):
    """El cliente consulta sus incidencias introduciendo su email."""
    incidencias = None
    email_buscado = ''

    if request.method == 'POST':
        email_buscado = request.POST.get('correo', '').strip().lower()
        if email_buscado:
            try:
                todos = DataverseClient().get_tickets()
                incidencias = [i for i in todos if i['correo'].lower() == email_buscado]
                if not incidencias:
                    messages.warning(request, 'No encontramos incidencias asociadas a ese correo.')
            except Exception as e:
                messages.error(request, f'Error al consultar las incidencias: {e}')
        else:
            messages.error(request, 'Introduce un correo válido.')

    return render(request, 'clientes/mis_incidencias.html', {
        'incidencias':   incidencias,
        'email_buscado': email_buscado,
    })
