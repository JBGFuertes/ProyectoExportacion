import json
import logging
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)
from django.conf import settings
from django.shortcuts import render
from django.contrib import messages
from comercial.api.dataverse import DataverseClient
from clientes.i18n import UI, get_lang


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
            'fecha':    (request.GET.get(f'p{i}_fecha', '') or '')[:10],
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
        gravedad_raw = request.POST.get(f'p{i}_gravedad', '').strip()
        try:
            gravedad = int(gravedad_raw)
        except (ValueError, TypeError):
            gravedad = None
        productos.append({
            'codigo':       request.POST.get(f'p{i}_codigo', '').strip(),
            'nombre':       request.POST.get(f'p{i}_nombre', '').strip(),
            'lote':         request.POST.get(f'p{i}_lote', '').strip(),
            'cantidad':     request.POST.get(f'p{i}_cantidad', '').strip(),
            'albaran':      request.POST.get(f'p{i}_albaran', '').strip(),
            'fecha':        request.POST.get(f'p{i}_fecha', '').strip(),
            'problema':     request.POST.get(f'p{i}_problema', '').strip(),
            'causageneral': request.POST.get(f'p{i}_causageneral', '').strip(),
            'causa':        request.POST.get(f'p{i}_causa', '').strip(),
            'gravedad':     gravedad,
        })
        i += 1
    return productos


def _causas_generales_bilingues(causas_catalogo):
    """Devuelve lista ordenada de pares únicos {es, en} de causageneral."""
    seen = set()
    result = []
    for c in causas_catalogo:
        es = c.get('causageneral', '')
        en = c.get('causageneral_en', '') or es
        if es and es not in seen:
            seen.add(es)
            result.append({'es': es, 'en': en})
    return result


def nueva_incidencia(request):
    """Formulario para que el cliente registre una nueva incidencia."""
    if request.method == 'POST':
        lang = get_lang(request)
        t = UI[lang]

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
        causas_bilingues = _causas_generales_bilingues(causas_catalogo)
        catalogo_ctx = {
            'causas_bilingues':      causas_bilingues,
            'causas_bilingues_json': json.dumps(causas_bilingues, ensure_ascii=False),
        }

        if not identificacion['empresa'] or not identificacion['correo']:
            messages.error(request, t['err_fields'])
            return render(request, 'clientes/nueva_incidencia.html', {
                'identificacion': identificacion,
                'productos':      productos,
                **catalogo_ctx,
            })

        if not productos:
            messages.error(request, t['err_products'])
            return render(request, 'clientes/nueva_incidencia.html', {
                'identificacion': identificacion,
                'productos':      productos,
                **catalogo_ctx,
            })

        # Lookup: causageneral (ES, clave interna) → primera causa específica del catálogo
        cg_a_primera_causa = {}
        for c in causas_catalogo:
            cg = c.get('causageneral', '')  # siempre clave ES
            if cg and cg not in cg_a_primera_causa:
                cg_a_primera_causa[cg] = c['nombre']

        SUFIJO_REVISAR = ' [REVISAR]'

        # Agrupar por causa específica (que PA usa para buscar en Dataverse)
        causas_agrupadas = {}
        for p in productos:
            causa_especifica = p.get('causa', '')
            causageneral     = p.get('causageneral', '')
            cliente_modifico = not bool(causa_especifica) and bool(causageneral)

            if cliente_modifico:
                causa_especifica = cg_a_primera_causa.get(causageneral, causageneral)

            clave = causa_especifica or causageneral or ''
            if clave not in causas_agrupadas:
                causas_agrupadas[clave] = {
                    'nombre':       causa_especifica,
                    'causageneral': causageneral,
                    'productos':    [],
                }
            problema = p.get('problema', '')
            if cliente_modifico:
                problema = problema + SUFIJO_REVISAR
            producto_data = {
                'codigo':   p.get('codigo', ''),
                'nombre':   p.get('nombre', ''),
                'lote':     p.get('lote', ''),
                'cantidad': p.get('cantidad', ''),
                'albaran':  p.get('albaran', ''),
                'fecha':    p.get('fecha', ''),
                'problema': problema,
            }
            if p.get('gravedad') is not None:
                producto_data['gravedad'] = p['gravedad']
            causas_agrupadas[clave]['productos'].append(producto_data)

        payload = {
            **identificacion,
            'causas': list(causas_agrupadas.values()),
        }

        url = settings.POWER_AUTOMATE_INCIDENCIAS_URL
        print('>>> PAYLOAD INCIDENCIA:', json.dumps(payload, ensure_ascii=False, indent=2))
        if url:
            try:
                r = requests.post(url, json=payload, timeout=30, verify=False)
                print('>>> POWER AUTOMATE STATUS:', r.status_code)
                print('>>> POWER AUTOMATE RESP:', r.text[:500])
                logger.info('Power Automate incidencias → %s: %s', r.status_code, r.text[:300])
            except Exception as e:
                print('>>> POWER AUTOMATE ERROR:', e)
                logger.error('Error llamando a Power Automate incidencias: %s', e)

        return render(request, 'clientes/nueva_incidencia.html', {'enviado': True})

    # GET: leer prefill de URL
    get_lang(request)  # persiste ?lang= en sesión si viene en la URL

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

    # Enriquecer productos del prefill: buscar causageneral (ES) y gravedad
    causa_lookup = {c['nombre']: c for c in causas_catalogo}
    for p in productos:
        match = causa_lookup.get(p.get('causa', ''), {})
        p['causageneral'] = match.get('causageneral', '')
        p['gravedad']     = match.get('gravedad_code', p.get('gravedad', ''))

    causas_bilingues = _causas_generales_bilingues(causas_catalogo)

    return render(request, 'clientes/nueva_incidencia.html', {
        'identificacion':        identificacion,
        'productos':             productos,
        'causas_bilingues':      causas_bilingues,
        'causas_bilingues_json': json.dumps(causas_bilingues, ensure_ascii=False),
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
