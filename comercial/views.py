import json
import requests
import urllib3
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

    return render(request, 'comercial/detalle_incidencia.html', {
        'incidencia': detalle['incidencia'],
        'grupos':     detalle['grupos'],
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
            material_id = cambio.get('id', '').strip()
            gravedad    = cambio.get('gravedad', '').strip()

            if gravedad not in valores_validos:
                return JsonResponse({'error': f'Gravedad no válida: {gravedad}'}, status=400)

            if material_id:
                client.update_gravedad_material(material_id, gravedad)

        return JsonResponse({'ok': True})

    except Exception:
        return JsonResponse({'error': 'Error al guardar las gravedades.'}, status=500)


@login_required
@require_POST
def ajustar_tono(request):
    """Llama a Power Automate para reescribir el texto en el tono solicitado."""
    try:
        body = json.loads(request.body)
        texto = body.get('texto', '').strip()
        tono = body.get('tono', '')

        if not texto or tono not in ('amigable', 'serio'):
            return JsonResponse({'error': 'Datos incorrectos.'}, status=400)

        url = settings.POWER_AUTOMATE_TONO_URL
        if not url:
            return JsonResponse({'error': 'URL de Power Automate no configurada.'}, status=500)

        payload = {
            'texto':    texto,
            'tono':     tono,
            'cliente':  body.get('cliente', ''),
            'gravedad': body.get('gravedad', ''),
            'causas':   body.get('causas', []),
        }

        respuesta = requests.post(url, json=payload, timeout=30, verify=False)
        respuesta.raise_for_status()
        datos = respuesta.json()
        return JsonResponse({'texto': datos.get('texto', '')})

    except requests.Timeout:
        return JsonResponse({'error': 'La IA tardó demasiado. Inténtalo de nuevo.'}, status=504)
    except Exception:
        return JsonResponse({'error': 'Error al contactar con la IA.'}, status=500)
