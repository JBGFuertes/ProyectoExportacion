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


INCIDENCIAS_MOCK = [
    {'id': '1',  'titulo': 'Producto dañado en envío',              'cliente': 'Distribuciones García',      'correo': 'garcia@ejemplo.com',    'estado': 'Pendiente',   'fecha': '2026-03-25'},
    {'id': '2',  'titulo': 'Error en cantidad facturada',            'cliente': 'Exportaciones Martín',       'correo': 'martin@ejemplo.com',    'estado': 'Procesando',  'fecha': '2026-03-26'},
    {'id': '3',  'titulo': 'Lote incorrecto recibido',               'cliente': 'Distribuciones García',      'correo': 'garcia@ejemplo.com',    'estado': 'Pendiente',   'fecha': '2026-03-27', 'derivada_calidad': True},
    {'id': '4',  'titulo': 'Retraso en entrega',                     'cliente': 'Comercial López',            'correo': 'lopez@ejemplo.com',     'estado': 'Finalizada',  'fecha': '2026-03-10'},
    {'id': '5',  'titulo': 'Producto caducado',                      'cliente': 'Importaciones Ruiz',         'correo': 'ruiz@ejemplo.com',      'estado': 'Pendiente',   'fecha': '2026-03-28'},
    {'id': '6',  'titulo': 'Albarán no coincide',                    'cliente': 'Comercial López',            'correo': 'lopez@ejemplo.com',     'estado': 'Procesando',  'fecha': '2026-03-29'},
    {'id': '7',  'titulo': 'Etiquetado incorrecto',                  'cliente': 'Mercadona SA',               'correo': 'mercadona@ejemplo.com', 'estado': 'Pendiente',   'fecha': '2026-03-30'},
    {'id': '8',  'titulo': 'Temperatura de transporte inadecuada',   'cliente': 'Carrefour España',           'correo': 'carrefour@ejemplo.com', 'estado': 'Procesando',  'fecha': '2026-03-29'},
    {'id': '9',  'titulo': 'Producto sin certificado de origen',     'cliente': 'Supermercados Día',          'correo': 'dia@ejemplo.com',       'estado': 'Finalizada',  'fecha': '2026-03-05'},
    {'id': '10', 'titulo': 'Embalaje deficiente',                    'cliente': 'Importaciones Ruiz',         'correo': 'ruiz@ejemplo.com',      'estado': 'Pendiente',   'fecha': '2026-03-31'},
    {'id': '11', 'titulo': 'Pedido incompleto',                      'cliente': 'Alcampo Distribución',       'correo': 'alcampo@ejemplo.com',   'estado': 'Procesando',  'fecha': '2026-03-28'},
    {'id': '12', 'titulo': 'Cambio de referencia sin aviso',         'cliente': 'Exportaciones Martín',       'correo': 'martin@ejemplo.com',    'estado': 'Finalizada',  'fecha': '2026-02-18'},
    {'id': '13', 'titulo': 'Falta documentación aduanera',           'cliente': 'Lidl España',                'correo': 'lidl@ejemplo.com',      'estado': 'Pendiente',   'fecha': '2026-03-31'},
    {'id': '14', 'titulo': 'Color anómalo en producto',              'cliente': 'Mercadona SA',               'correo': 'mercadona@ejemplo.com', 'estado': 'Procesando',  'fecha': '2026-03-27'},
    {'id': '15', 'titulo': 'Discrepancia en peso neto',              'cliente': 'Carrefour España',           'correo': 'carrefour@ejemplo.com', 'estado': 'Finalizada',  'fecha': '2026-02-28'},
    {'id': '16', 'titulo': 'Fecha de consumo preferente incorrecta', 'cliente': 'Distribuciones García',      'correo': 'garcia@ejemplo.com',    'estado': 'Pendiente',   'fecha': '2026-03-30'},
    {'id': '17', 'titulo': 'Merma excesiva en tránsito',             'cliente': 'Alcampo Distribución',       'correo': 'alcampo@ejemplo.com',   'estado': 'Procesando',  'fecha': '2026-03-26'},
    {'id': '18', 'titulo': 'Envase con presencia de cuerpo extraño', 'cliente': 'Supermercados Día',          'correo': 'dia@ejemplo.com',       'estado': 'Finalizada',  'fecha': '2026-02-10', 'derivada_calidad': True},
    {'id': '19', 'titulo': 'Error en código de barras',              'cliente': 'Lidl España',                'correo': 'lidl@ejemplo.com',      'estado': 'Pendiente',   'fecha': '2026-03-29'},
    {'id': '20', 'titulo': 'Rotura de cadena de frío',               'cliente': 'Comercial López',            'correo': 'lopez@ejemplo.com',     'estado': 'Procesando',  'fecha': '2026-03-25'},
    {'id': '21', 'titulo': 'Producto con moho visible',              'cliente': 'Mercadona SA',               'correo': 'mercadona@ejemplo.com', 'estado': 'Finalizada',  'fecha': '2026-01-30', 'derivada_calidad': True},
    {'id': '22', 'titulo': 'Alergenos no declarados en etiqueta',    'cliente': 'Importaciones Ruiz',         'correo': 'ruiz@ejemplo.com',      'estado': 'Pendiente',   'fecha': '2026-03-28', 'derivada_calidad': True},
    {'id': '23', 'titulo': 'Pedido duplicado en sistema',            'cliente': 'Exportaciones Martín',       'correo': 'martin@ejemplo.com',    'estado': 'Procesando',  'fecha': '2026-03-24'},
    {'id': '24', 'titulo': 'Daños en palets por manipulación',       'cliente': 'Carrefour España',           'correo': 'carrefour@ejemplo.com', 'estado': 'Pendiente',   'fecha': '2026-03-27'},
    {'id': '25', 'titulo': 'Factura con IVA incorrecto',             'cliente': 'Alcampo Distribución',       'correo': 'alcampo@ejemplo.com',   'estado': 'Finalizada',  'fecha': '2026-02-05'},
    {'id': '26', 'titulo': 'Incidencia en aduanas destino',          'cliente': 'Lidl España',                'correo': 'lidl@ejemplo.com',      'estado': 'Procesando',  'fecha': '2026-03-23'},
    {'id': '27', 'titulo': 'Producto con olor anómalo',              'cliente': 'Supermercados Día',          'correo': 'dia@ejemplo.com',       'estado': 'Pendiente',   'fecha': '2026-03-26'},
    {'id': '28', 'titulo': 'Exceso de unidades enviadas',            'cliente': 'Distribuciones García',      'correo': 'garcia@ejemplo.com',    'estado': 'Procesando',  'fecha': '2026-03-22'},
    {'id': '29', 'titulo': 'Cambio de formato no comunicado',        'cliente': 'Comercial López',            'correo': 'lopez@ejemplo.com',     'estado': 'Pendiente',   'fecha': '2026-03-25'},
    {'id': '30', 'titulo': 'Retraso por huelga de transporte',       'cliente': 'Mercadona SA',               'correo': 'mercadona@ejemplo.com', 'estado': 'Finalizada',  'fecha': '2026-01-15'},
    {'id': '31', 'titulo': 'Contaminación cruzada detectada',        'cliente': 'Carrefour España',           'correo': 'carrefour@ejemplo.com', 'estado': 'Procesando',  'fecha': '2026-03-21', 'derivada_calidad': True},
    {'id': '32', 'titulo': 'Sellado deficiente en envase',           'cliente': 'Importaciones Ruiz',         'correo': 'ruiz@ejemplo.com',      'estado': 'Pendiente',   'fecha': '2026-03-24'},
    {'id': '33', 'titulo': 'Diferencia de precio facturado',         'cliente': 'Exportaciones Martín',       'correo': 'martin@ejemplo.com',    'estado': 'Finalizada',  'fecha': '2026-02-20'},
    {'id': '34', 'titulo': 'Rotura de stock sin aviso previo',       'cliente': 'Alcampo Distribución',       'correo': 'alcampo@ejemplo.com',   'estado': 'Pendiente',   'fecha': '2026-03-23'},
    {'id': '35', 'titulo': 'Producto rechazado en destino',          'cliente': 'Lidl España',                'correo': 'lidl@ejemplo.com',      'estado': 'Procesando',  'fecha': '2026-03-20'},
    {'id': '36', 'titulo': 'Humedad excesiva en almacén origen',     'cliente': 'Supermercados Día',          'correo': 'dia@ejemplo.com',       'estado': 'Pendiente',   'fecha': '2026-03-22'},
]

PRODUCTOS_MOCK = {
    '1': [
        {'nombre': 'Aceite de Oliva 5L', 'codigo': 'AOL-001', 'cantidad': 24, 'lote': 'L2024-01', 'albaran': 'ALB-2024-001', 'problema': 'Envase roto', 'gravedad': 'Moderada', 'fecha': '2026-03-24'},
        {'nombre': 'Aceite de Girasol 1L', 'codigo': 'AGI-002', 'cantidad': 48, 'lote': 'L2024-02', 'albaran': 'ALB-2024-001', 'problema': 'Fuga en tapón', 'gravedad': 'Leve', 'fecha': '2026-03-24'},
    ],
    '2': [
        {'nombre': 'Vinagre de Vino 750ml', 'codigo': 'VIN-005', 'cantidad': 12, 'lote': 'L2024-05', 'albaran': 'ALB-2024-002', 'problema': 'Cantidad incorrecta en factura', 'gravedad': 'Leve', 'fecha': '2026-03-25'},
    ],
    '3': [
        {'nombre': 'Aceite de Oliva 5L', 'codigo': 'AOL-001', 'cantidad': 36, 'lote': 'L2024-99', 'albaran': 'ALB-2024-003', 'problema': 'Lote no solicitado', 'gravedad': 'Grave', 'fecha': '2026-03-26'},
    ],
    '4': [
        {'nombre': 'Mermelada Fresa 500g', 'codigo': 'MER-010', 'cantidad': 60, 'lote': 'L2024-10', 'albaran': 'ALB-2024-004', 'problema': 'Entrega fuera de plazo', 'gravedad': 'Leve', 'fecha': '2026-03-09'},
        {'nombre': 'Mermelada Naranja 500g', 'codigo': 'MER-011', 'cantidad': 60, 'lote': 'L2024-11', 'albaran': 'ALB-2024-004', 'problema': 'Entrega fuera de plazo', 'gravedad': 'Leve', 'fecha': '2026-03-09'},
    ],
    '5': [
        {'nombre': 'Zumo de Naranja 1L', 'codigo': 'ZUM-020', 'cantidad': 36, 'lote': 'L2024-20', 'albaran': 'ALB-2024-005', 'problema': 'Fecha de caducidad superada', 'gravedad': 'Grave', 'fecha': '2026-03-27'},
        {'nombre': 'Zumo de Mango 1L', 'codigo': 'ZUM-021', 'cantidad': 24, 'lote': 'L2024-21', 'albaran': 'ALB-2024-005', 'problema': 'Fecha de caducidad superada', 'gravedad': 'Grave', 'fecha': '2026-03-27'},
        {'nombre': 'Zumo de Piña 1L', 'codigo': 'ZUM-022', 'cantidad': 12, 'lote': 'L2024-21', 'albaran': 'ALB-2024-005', 'problema': 'Fecha de caducidad superada', 'gravedad': 'Grave', 'fecha': '2026-03-27'},
    ],
    '6': [
        {'nombre': 'Conserva Tomate 800g', 'codigo': 'CON-030', 'cantidad': 48, 'lote': 'L2024-30', 'albaran': 'ALB-2024-006', 'problema': 'Número de albarán no coincide con pedido', 'gravedad': 'Moderada', 'fecha': '2026-03-28'},
    ],
    '7': [
        {'nombre': 'Lomo Embuchado 200g', 'codigo': 'LOM-040', 'cantidad': 120, 'lote': 'L2026-07', 'albaran': 'ALB-2026-007', 'problema': 'Etiqueta sin información de alérgenos', 'gravedad': 'Grave', 'fecha': '2026-03-29'},
        {'nombre': 'Chorizo Extra 250g', 'codigo': 'CHO-041', 'cantidad': 96, 'lote': 'L2026-08', 'albaran': 'ALB-2026-007', 'problema': 'Código de barras ilegible', 'gravedad': 'Leve', 'fecha': '2026-03-29'},
    ],
    '8': [
        {'nombre': 'Jamón Cocido Loncheado 150g', 'codigo': 'JAM-050', 'cantidad': 200, 'lote': 'L2026-09', 'albaran': 'ALB-2026-008', 'problema': 'Temperatura en camión superior a 5°C', 'gravedad': 'Grave', 'fecha': '2026-03-28'},
    ],
    '9': [
        {'nombre': 'Salchichón Ibérico 300g', 'codigo': 'SAL-060', 'cantidad': 80, 'lote': 'L2026-10', 'albaran': 'ALB-2026-009', 'problema': 'No incluye certificado DOP adjunto', 'gravedad': 'Moderada', 'fecha': '2026-03-04'},
    ],
    '10': [
        {'nombre': 'Morcilla de Burgos 400g', 'codigo': 'MOR-070', 'cantidad': 60, 'lote': 'L2026-11', 'albaran': 'ALB-2026-010', 'problema': 'Caja exterior sin protección adecuada', 'gravedad': 'Leve', 'fecha': '2026-03-30'},
        {'nombre': 'Butifarra Cocida 350g', 'codigo': 'BUT-071', 'cantidad': 40, 'lote': 'L2026-12', 'albaran': 'ALB-2026-010', 'problema': 'Embalaje interior roto', 'gravedad': 'Moderada', 'fecha': '2026-03-30'},
    ],
    '11': [
        {'nombre': 'Fuet Extra 180g', 'codigo': 'FUE-080', 'cantidad': 150, 'lote': 'L2026-13', 'albaran': 'ALB-2026-011', 'problema': 'Faltan 30 unidades del pedido', 'gravedad': 'Moderada', 'fecha': '2026-03-27'},
    ],
    '12': [
        {'nombre': 'Chorizo Picante 200g', 'codigo': 'CHO-090', 'cantidad': 100, 'lote': 'L2026-14', 'albaran': 'ALB-2026-012', 'problema': 'Código de referencia cambiado sin notificación', 'gravedad': 'Leve', 'fecha': '2026-02-17'},
    ],
    '13': [
        {'nombre': 'Jamón Serrano Loncheado 100g', 'codigo': 'JSE-100', 'cantidad': 300, 'lote': 'L2026-15', 'albaran': 'ALB-2026-013', 'problema': 'Certificado sanitario no incluido en envío', 'gravedad': 'Grave', 'fecha': '2026-03-30'},
        {'nombre': 'Paleta Ibérica 100g', 'codigo': 'PAL-101', 'cantidad': 200, 'lote': 'L2026-16', 'albaran': 'ALB-2026-013', 'problema': 'Documentación aduanera incompleta', 'gravedad': 'Grave', 'fecha': '2026-03-30'},
    ],
    '14': [
        {'nombre': 'Morcón Ibérico 250g', 'codigo': 'MRC-110', 'cantidad': 50, 'lote': 'L2026-17', 'albaran': 'ALB-2026-014', 'problema': 'Coloración verdosa en corte', 'gravedad': 'Grave', 'fecha': '2026-03-26'},
    ],
    '15': [
        {'nombre': 'Lomo Adobado 180g', 'codigo': 'LOA-120', 'cantidad': 180, 'lote': 'L2026-18', 'albaran': 'ALB-2026-015', 'problema': 'Peso declarado 180g, real 162g', 'gravedad': 'Moderada', 'fecha': '2026-02-27'},
        {'nombre': 'Chistorra 300g', 'codigo': 'CHI-121', 'cantidad': 90, 'lote': 'L2026-19', 'albaran': 'ALB-2026-015', 'problema': 'Peso declarado 300g, real 280g', 'gravedad': 'Leve', 'fecha': '2026-02-27'},
    ],
    '16': [
        {'nombre': 'Salchicha Frankfurt 250g', 'codigo': 'SFR-130', 'cantidad': 240, 'lote': 'L2026-20', 'albaran': 'ALB-2026-016', 'problema': 'Fecha impresa 2025 en lugar de 2026', 'gravedad': 'Grave', 'fecha': '2026-03-29'},
    ],
    '17': [
        {'nombre': 'Jamón York 200g', 'codigo': 'JYO-140', 'cantidad': 160, 'lote': 'L2026-21', 'albaran': 'ALB-2026-017', 'problema': 'Merma del 12% respecto al pedido', 'gravedad': 'Moderada', 'fecha': '2026-03-25'},
    ],
    '18': [
        {'nombre': 'Paté de Hígado 125g', 'codigo': 'PAT-150', 'cantidad': 72, 'lote': 'L2026-22', 'albaran': 'ALB-2026-018', 'problema': 'Fragmento metálico detectado en interior', 'gravedad': 'Grave', 'fecha': '2026-02-09'},
    ],
    '19': [
        {'nombre': 'Chorizo Ibérico 150g', 'codigo': 'CHI-160', 'cantidad': 200, 'lote': 'L2026-23', 'albaran': 'ALB-2026-019', 'problema': 'Código EAN13 no escaneable', 'gravedad': 'Moderada', 'fecha': '2026-03-28'},
        {'nombre': 'Lomo Ibérico 100g', 'codigo': 'LIB-161', 'cantidad': 150, 'lote': 'L2026-24', 'albaran': 'ALB-2026-019', 'problema': 'Código DataMatrix ilegible', 'gravedad': 'Leve', 'fecha': '2026-03-28'},
    ],
    '20': [
        {'nombre': 'Pechuga de Pavo 200g', 'codigo': 'PAV-170', 'cantidad': 300, 'lote': 'L2026-25', 'albaran': 'ALB-2026-020', 'problema': 'Temperatura de llegada 12°C (máx. 4°C)', 'gravedad': 'Grave', 'fecha': '2026-03-24'},
    ],
    '21': [
        {'nombre': 'Queso Manchego Tierno 250g', 'codigo': 'QMT-180', 'cantidad': 48, 'lote': 'L2026-26', 'albaran': 'ALB-2026-021', 'problema': 'Moho negro en superficie', 'gravedad': 'Grave', 'fecha': '2026-01-29'},
    ],
    '22': [
        {'nombre': 'Mortadela con Aceitunas 200g', 'codigo': 'MRT-190', 'cantidad': 130, 'lote': 'L2026-27', 'albaran': 'ALB-2026-022', 'problema': 'Gluten no declarado en etiqueta', 'gravedad': 'Grave', 'fecha': '2026-03-27'},
        {'nombre': 'Salami Ahumado 150g', 'codigo': 'SLA-191', 'cantidad': 80, 'lote': 'L2026-28', 'albaran': 'ALB-2026-022', 'problema': 'Lactosa no declarada en etiqueta', 'gravedad': 'Grave', 'fecha': '2026-03-27'},
    ],
    '23': [
        {'nombre': 'Jamón Cocido Extra 300g', 'codigo': 'JCE-200', 'cantidad': 400, 'lote': 'L2026-29', 'albaran': 'ALB-2026-023', 'problema': 'Pedido recibido dos veces mismo día', 'gravedad': 'Leve', 'fecha': '2026-03-23'},
    ],
    '24': [
        {'nombre': 'Chorizo de Pamplona 500g', 'codigo': 'CHP-210', 'cantidad': 60, 'lote': 'L2026-30', 'albaran': 'ALB-2026-024', 'problema': 'Palets caídos, producto aplastado', 'gravedad': 'Moderada', 'fecha': '2026-03-26'},
    ],
    '25': [
        {'nombre': 'Fuet Selección 220g', 'codigo': 'FSE-220', 'cantidad': 110, 'lote': 'L2026-31', 'albaran': 'ALB-2026-025', 'problema': 'IVA aplicado 10% en lugar de 4%', 'gravedad': 'Leve', 'fecha': '2026-02-04'},
    ],
    '26': [
        {'nombre': 'Jamón Ibérico Bellota 80g', 'codigo': 'JIB-230', 'cantidad': 500, 'lote': 'L2026-32', 'albaran': 'ALB-2026-026', 'problema': 'Retenido en aduana por documentación', 'gravedad': 'Grave', 'fecha': '2026-03-22'},
        {'nombre': 'Paleta Ibérica Bellota 80g', 'codigo': 'PIB-231', 'cantidad': 300, 'lote': 'L2026-33', 'albaran': 'ALB-2026-026', 'problema': 'Retenido en aduana por documentación', 'gravedad': 'Grave', 'fecha': '2026-03-22'},
    ],
    '27': [
        {'nombre': 'Morcilla de Arroz 400g', 'codigo': 'MAR-240', 'cantidad': 70, 'lote': 'L2026-34', 'albaran': 'ALB-2026-027', 'problema': 'Olor a rancio al abrir envase', 'gravedad': 'Grave', 'fecha': '2026-03-25'},
    ],
    '28': [
        {'nombre': 'Lomo en Manteca 300g', 'codigo': 'LMN-250', 'cantidad': 200, 'lote': 'L2026-35', 'albaran': 'ALB-2026-028', 'problema': 'Enviadas 200 unidades, pedido era 150', 'gravedad': 'Leve', 'fecha': '2026-03-21'},
    ],
    '29': [
        {'nombre': 'Chorizo Extra Bandeja 6u', 'codigo': 'CHB-260', 'cantidad': 90, 'lote': 'L2026-36', 'albaran': 'ALB-2026-029', 'problema': 'Formato cambiado de 6u a 4u sin aviso', 'gravedad': 'Moderada', 'fecha': '2026-03-24'},
    ],
    '30': [
        {'nombre': 'Salchichón Extra 200g', 'codigo': 'SLE-270', 'cantidad': 250, 'lote': 'L2026-37', 'albaran': 'ALB-2026-030', 'problema': 'Retraso 5 días por huelga transportistas', 'gravedad': 'Leve', 'fecha': '2026-01-14'},
    ],
    '31': [
        {'nombre': 'Pollo Asado Loncheado 150g', 'codigo': 'POL-280', 'cantidad': 180, 'lote': 'L2026-38', 'albaran': 'ALB-2026-031', 'problema': 'Restos de cerdo en línea de producción', 'gravedad': 'Grave', 'fecha': '2026-03-20'},
        {'nombre': 'Pavo Asado Loncheado 150g', 'codigo': 'PAL-281', 'cantidad': 120, 'lote': 'L2026-39', 'albaran': 'ALB-2026-031', 'problema': 'Posible contaminación alérgeno', 'gravedad': 'Grave', 'fecha': '2026-03-20'},
    ],
    '32': [
        {'nombre': 'Jamón Serrano Gran Reserva 80g', 'codigo': 'JSG-290', 'cantidad': 350, 'lote': 'L2026-40', 'albaran': 'ALB-2026-032', 'problema': 'Sellado termosellado roto en 40 unidades', 'gravedad': 'Moderada', 'fecha': '2026-03-23'},
    ],
    '33': [
        {'nombre': 'Cecina de León 100g', 'codigo': 'CEC-300', 'cantidad': 60, 'lote': 'L2026-41', 'albaran': 'ALB-2026-033', 'problema': 'Precio facturado 3,20€ vs tarifa acordada 2,80€', 'gravedad': 'Moderada', 'fecha': '2026-02-19'},
    ],
    '34': [
        {'nombre': 'Chorizo Riojano 180g', 'codigo': 'CHR-310', 'cantidad': 400, 'lote': 'L2026-42', 'albaran': 'ALB-2026-034', 'problema': 'Sin stock disponible 3 días sin comunicar', 'gravedad': 'Moderada', 'fecha': '2026-03-22'},
        {'nombre': 'Longaniza 200g', 'codigo': 'LON-311', 'cantidad': 200, 'lote': 'L2026-43', 'albaran': 'ALB-2026-034', 'problema': 'Sin stock disponible 3 días sin comunicar', 'gravedad': 'Leve', 'fecha': '2026-03-22'},
    ],
    '35': [
        {'nombre': 'Jamón Ibérico Cebo 100g', 'codigo': 'JIC-320', 'cantidad': 600, 'lote': 'L2026-44', 'albaran': 'ALB-2026-035', 'problema': 'Rechazado por cliente por temperatura incorrecta', 'gravedad': 'Grave', 'fecha': '2026-03-19'},
    ],
    '36': [
        {'nombre': 'Sobrasada Mallorquina 200g', 'codigo': 'SOB-330', 'cantidad': 90, 'lote': 'L2026-45', 'albaran': 'ALB-2026-036', 'problema': 'Humedad 85% en almacén, producto afectado', 'gravedad': 'Grave', 'fecha': '2026-03-21'},
        {'nombre': 'Botifarra Negra 300g', 'codigo': 'BOT-331', 'cantidad': 60, 'lote': 'L2026-46', 'albaran': 'ALB-2026-036', 'problema': 'Condensación en interior de envases', 'gravedad': 'Moderada', 'fecha': '2026-03-21'},
    ],
}


@login_required
def dashboard(request):
    pendientes = [i for i in INCIDENCIAS_MOCK if i['estado'] == 'Pendiente']
    procesando = [i for i in INCIDENCIAS_MOCK if i['estado'] == 'Procesando']
    finalizadas = [i for i in INCIDENCIAS_MOCK if i['estado'] == 'Finalizada']

    calidad = [i for i in INCIDENCIAS_MOCK if i.get('derivada_calidad')]
    context = {
        'incidencias': INCIDENCIAS_MOCK,
        'total_pendientes': len(pendientes),
        'total_procesando': len(procesando),
        'total_finalizadas': len(finalizadas),
        'total_calidad': len(calidad),
    }
    return render(request, 'comercial/dashboard.html', context)


@login_required
def detalle_incidencia(request, incidencia_id):
    incidencia = next((i for i in INCIDENCIAS_MOCK if i['id'] == incidencia_id), None)
    if not incidencia:
        return redirect('comercial:dashboard')
    productos = PRODUCTOS_MOCK.get(incidencia_id, [])
    return render(request, 'comercial/detalle_incidencia.html', {
        'incidencia': incidencia,
        'productos': productos,
    })


@login_required
@require_POST
def derivar_calidad(request, incidencia_id):
    """Marca una incidencia como derivada al departamento de Calidad."""
    incidencia = next((i for i in INCIDENCIAS_MOCK if i['id'] == incidencia_id), None)
    if not incidencia:
        return JsonResponse({'error': 'Incidencia no encontrada.'}, status=404)
    incidencia['derivada_calidad'] = True
    # TODO Dataverse: dataverse_client.update_incidencia(incidencia_id, {'derivada_calidad': True})
    return JsonResponse({'ok': True})


@login_required
@require_POST
def actualizar_gravedades(request, incidencia_id):
    """Actualiza la gravedad de los productos de una incidencia."""
    try:
        body = json.loads(request.body)
        productos = body.get('productos', [])

        if incidencia_id not in PRODUCTOS_MOCK:
            return JsonResponse({'error': 'Incidencia no encontrada.'}, status=404)

        valores_validos = {'Leve', 'Moderada', 'Grave'}
        for cambio in productos:
            codigo = cambio.get('codigo', '').strip()
            gravedad = cambio.get('gravedad', '').strip()
            if gravedad not in valores_validos:
                return JsonResponse({'error': f'Gravedad no válida: {gravedad}'}, status=400)
            for prod in PRODUCTOS_MOCK[incidencia_id]:
                if prod['codigo'] == codigo:
                    prod['gravedad'] = gravedad
                    break

        # TODO Dataverse: dataverse_client.update_gravedades_productos(incidencia_id, productos)
        # Nota: el mock se actualiza en memoria — los cambios se pierden al reiniciar el servidor.

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

        respuesta = requests.post(url, json={'texto': texto, 'tono': tono}, timeout=30, verify=False)
        respuesta.raise_for_status()
        datos = respuesta.json()
        return JsonResponse({'texto': datos.get('texto', '')})

    except requests.Timeout:
        return JsonResponse({'error': 'La IA tardó demasiado. Inténtalo de nuevo.'}, status=504)
    except Exception as e:
        return JsonResponse({'error': 'Error al contactar con la IA.'}, status=500)
