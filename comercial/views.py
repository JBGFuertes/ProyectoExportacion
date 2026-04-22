import base64
import json
import logging
import requests
import urllib3

logger = logging.getLogger(__name__)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from comercial.api.dataverse import DataverseClient


def login_view(request):
    if request.user.is_authenticated:
        return redirect('comercial:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('comercial:dashboard')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')

    return render(request, 'comercial/login.html')


def logout_view(request):
    logout(request)
    return redirect('comercial:login')


@login_required
def dashboard(request):
    try:
        incidencias = DataverseClient().get_tickets()
    except Exception as e:
        messages.error(request, f'Error al conectar con Dataverse: {e}')
        incidencias = []

    pendientes = [i for i in incidencias if i['estado'] == 'Pendiente']
    procesando = [i for i in incidencias if i['estado'] == 'Procesando']
    finalizadas = [i for i in incidencias if i['estado'] == 'Finalizada']
    calidad     = [i for i in incidencias if i.get('derivada_calidad')]

    return render(request, 'comercial/dashboard.html', {
        'incidencias':       incidencias,
        'total_pendientes':  len(pendientes),
        'total_procesando':  len(procesando),
        'total_finalizadas': len(finalizadas),
        'total_calidad':     len(calidad),
    })


@login_required
def detalle_incidencia(request, incidencia_id):
    try:
        detalle = DataverseClient().get_ticket_detail(incidencia_id)
    except Exception:
        return redirect('comercial:dashboard')

    if not detalle:
        return redirect('comercial:dashboard')

    # Catálogo de causas activas (para las opciones del select)
    try:
        causas_catalogo = DataverseClient().get_causes_catalog()
    except Exception:
        causas_catalogo = []

    # Mapeo nombre → ticket_cause_id (todas las causas del ticket, no solo las que tienen materiales)
    causa_id_por_nombre = detalle.get('all_ticket_causes', {})

    return render(request, 'comercial/detalle_incidencia.html', {
        'incidencia':          detalle['incidencia'],
        'grupos':              detalle['grupos'],
        'causas_catalogo_json': json.dumps(causas_catalogo, ensure_ascii=False),
        'causa_id_map_json':   json.dumps(causa_id_por_nombre, ensure_ascii=False),
    })


@login_required
@require_POST
def derivar_calidad(request, incidencia_id):
    # TODO: implementar campo en Dataverse para marcar derivada a calidad
    return JsonResponse({'ok': True})


@login_required
@require_POST
def actualizar_gravedades(request, incidencia_id):
    """
    Actualiza la gravedad de productos individuales.
    Payload: {productos: [{id, codigo, gravedad}]}
    """
    try:
        body = json.loads(request.body)
        productos = body.get('productos', [])
        valores_validos = {'Leve', 'Moderada', 'Grave'}

        client = DataverseClient()
        for cambio in productos:
            material_id       = cambio.get('id', '').strip()
            gravedad          = cambio.get('gravedad', '').strip()
            causa_id          = cambio.get('causa_id', '').strip()
            causa_nombre      = cambio.get('causa_nombre', '').strip()
            causa_catalog_id  = cambio.get('causa_catalog_id', '').strip()
            causa_id_original = cambio.get('causa_id_original', '').strip()

            if gravedad not in valores_validos:
                return JsonResponse({'error': f'Gravedad no válida: {gravedad}'}, status=400)

            if not material_id:
                continue

            # Si la causa no existe aún en el ticket, crearla
            if not causa_id and causa_nombre:
                causa_id = client.create_ticket_cause(incidencia_id, causa_nombre, causa_catalog_id)

            client.update_material(material_id, gravedad, causa_id or None)

            # Si el material cambió de causa, borrar la causa vieja si quedó sin materiales
            if causa_id_original and causa_id and causa_id_original != causa_id:
                client.delete_ticket_cause_if_empty(causa_id_original)

        return JsonResponse({'ok': True})

    except Exception as e:
        return JsonResponse({'error': f'Error al guardar: {e}'}, status=500)


@login_required
@require_POST
def enviar_respuesta(request, incidencia_id):
    """Envía la respuesta al cliente por email via Power Automate."""
    texto = request.POST.get('texto', '').strip()
    if not texto:
        return JsonResponse({'error': 'El texto no puede estar vacío.'}, status=400)

    url = settings.POWER_AUTOMATE_EMAIL_REPLY_URL
    if not url:
        return JsonResponse({'error': 'URL de envío de email no configurada.'}, status=500)

    try:
        datos = DataverseClient().get_ticket_reply_data(incidencia_id)
    except Exception as e:
        return JsonResponse({'error': f'Error obteniendo datos del ticket: {e}'}, status=500)

    if not datos['destinatario']:
        return JsonResponse({'error': 'El ticket no tiene correo de cliente.'}, status=400)
    if not datos['message_id']:
        return JsonResponse({'error': 'Este ticket no tiene message_id: fue creado sin email original y no se puede responder por correo.'}, status=400)

    logger.info('Enviando respuesta email — destinatario: %s | conversation_id: %s | message_id: %s',
                datos['destinatario'], datos['conversation_id'], datos['message_id'])

    adjuntos = []
    for f in request.FILES.getlist('adjuntos'):
        adjuntos.append({
            'Name':         f.name,
            'ContentBytes': base64.b64encode(f.read()).decode('utf-8'),
        })

    payload = {
        'destinatario':    datos['destinatario'],
        'conversation_id': datos['conversation_id'],
        'message_id':      datos['message_id'],
        'cuerpo':          texto,
        'adjuntos':        adjuntos,
    }

    try:
        r = requests.post(url, json=payload, timeout=60, verify=False)
        r.raise_for_status()
        return JsonResponse({'ok': True})
    except requests.Timeout:
        return JsonResponse({'error': 'Tiempo de espera agotado. Inténtalo de nuevo.'}, status=504)
    except Exception as e:
        return JsonResponse({'error': f'Error al enviar: {e}'}, status=500)


@login_required
@require_POST
def ajustar_tono(request):
    """Llama a Power Automate para reescribir el texto en el tono solicitado."""
    try:
        body = json.loads(request.body)
        texto = body.get('texto', '').strip()
        tono = body.get('tono', '')

        if not texto or tono not in ('amigable', 'formal'):
            return JsonResponse({'error': 'Datos incorrectos.'}, status=400)

        url = 'http://scloudw040:1084/Endpoint_Incidencias/api/incidencias/consulta'

        payload = {
            'texto':    texto,
            'tono':     tono,
            'cliente':  body.get('cliente', ''),
            'gravedad': body.get('gravedad', ''),
            'causas':   body.get('causas', []),
        }

        respuesta = requests.post(url, json=payload, timeout=120, verify=False)
        respuesta.raise_for_status()
        datos = respuesta.json()
        logger.info('Respuesta endpoint tono: %s', datos)
        texto = datos.get('content', '')
        if not texto:
            return JsonResponse({'error': f'El endpoint no devolvió "content". Respuesta recibida: {datos}'})
        return JsonResponse({'texto': texto})

    except requests.Timeout:
        return JsonResponse({'error': 'La IA tardó demasiado. Inténtalo de nuevo.'}, status=504)
    except Exception as e:
        return JsonResponse({'error': f'Error al contactar con la IA: {e}'}, status=500)
