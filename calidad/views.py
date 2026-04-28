import json
import logging
import requests
import urllib3

logger = logging.getLogger(__name__)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from comercial.api.dataverse import DataverseClient


@login_required
def dashboard(request):
    try:
        incidencias = DataverseClient().get_tickets_calidad()
    except Exception as e:
        messages.error(request, f'Error al conectar con Dataverse: {e}')
        incidencias = []

    pendientes  = [i for i in incidencias if i['estado'] == 'Pendiente']
    procesando  = [i for i in incidencias if i['estado'] == 'Procesando']
    finalizadas = [i for i in incidencias if i['estado'] == 'Finalizada']

    return render(request, 'calidad/dashboard.html', {
        'incidencias':       incidencias,
        'total_pendientes':  len(pendientes),
        'total_procesando':  len(procesando),
        'total_finalizadas': len(finalizadas),
    })


@login_required
def detalle_incidencia(request, incidencia_id):
    try:
        detalle = DataverseClient().get_ticket_detail_calidad(incidencia_id)
    except Exception:
        return redirect('calidad:dashboard')

    if not detalle:
        return redirect('calidad:dashboard')

    try:
        causas_catalogo = DataverseClient().get_causes_catalog()
    except Exception:
        causas_catalogo = []

    SUFIJO_REVISAR = ' [REVISAR]'
    for grupo in detalle.get('grupos', []):
        for subgrupo in grupo.get('subgrupos', []):
            for m in subgrupo.get('productos', []):
                if m.get('problema', '').endswith(SUFIJO_REVISAR):
                    m['revisable'] = True
                    m['problema']  = m['problema'][:-len(SUFIJO_REVISAR)]
                else:
                    m['revisable'] = False

    causa_id_por_nombre = detalle.get('all_ticket_causes', {})

    return render(request, 'calidad/detalle_incidencia.html', {
        'incidencia':           detalle['incidencia'],
        'grupos':               detalle['grupos'],
        'causas_catalogo_json': json.dumps(causas_catalogo, ensure_ascii=False),
        'causa_id_map_json':    json.dumps(causa_id_por_nombre, ensure_ascii=False),
    })


@login_required
@require_POST
def generar_respuesta(request):
    """Llama al endpoint IA de calidad para generar texto interno."""
    try:
        body = json.loads(request.body)
        texto   = body.get('texto', '').strip()
        causas  = body.get('causas', [])

        if not texto:
            return JsonResponse({'error': 'El texto no puede estar vacío.'}, status=400)

        url = settings.CALIDAD_AI_ENDPOINT
        if not url:
            return JsonResponse({'error': 'Endpoint de IA de calidad no configurado.'}, status=500)

        payload = {
            'texto':    texto,
            'cliente':  body.get('cliente', ''),
            'idioma':   body.get('idioma', ''),
            'gravedad': body.get('gravedad', ''),
            'causas':   causas,
        }

        respuesta = requests.post(url, json=payload, timeout=120, verify=False)
        respuesta.raise_for_status()
        datos = respuesta.json()
        texto_generado = datos.get('content', '')
        if not texto_generado:
            return JsonResponse({'error': f'El endpoint no devolvió "content". Respuesta: {datos}'})
        return JsonResponse({'texto': texto_generado})

    except requests.Timeout:
        return JsonResponse({'error': 'La IA tardó demasiado. Inténtalo de nuevo.'}, status=504)
    except Exception as e:
        return JsonResponse({'error': f'Error al contactar con la IA: {e}'}, status=500)
