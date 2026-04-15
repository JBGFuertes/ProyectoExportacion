"""
Cliente para la API de Microsoft Dataverse.
Toda la lógica de conexión y consultas está aquí.
Para cambiar de fuente de datos en el futuro, solo hay que modificar este fichero.
"""
import msal
import requests
import urllib3
from django.conf import settings

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Mapeos entre valores numéricos de Dataverse y strings legibles
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

GRAVEDAD_REVERSE = {v: k for k, v in GRAVEDAD_MAP.items()}


class DataverseClient:

    def __init__(self):
        self.client_id     = settings.AZURE_CLIENT_ID
        self.client_secret = settings.AZURE_CLIENT_SECRET
        self.tenant_id     = settings.AZURE_TENANT_ID
        self.resource      = settings.DATAVERSE_URL.rstrip('/')
        self.base_url      = self.resource + '/api/data/v9.2'

    def _get_token(self):
        app = msal.ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=f'https://login.microsoftonline.com/{self.tenant_id}',
        )
        result = app.acquire_token_for_client(scopes=[f'{self.resource}/.default'])
        if 'access_token' not in result:
            raise Exception(f"Error obteniendo token Azure: {result.get('error_description', 'desconocido')}")
        return result['access_token']

    def _headers(self):
        return {
            'Authorization': f'Bearer {self._get_token()}',
            'OData-MaxVersion': '4.0',
            'OData-Version': '4.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }

    def _get(self, endpoint, params=None):
        url = f'{self.base_url}/{endpoint}'
        r = requests.get(url, headers=self._headers(), params=params, verify=False, timeout=30)
        r.raise_for_status()
        return r.json()

    def _patch(self, endpoint, data):
        url = f'{self.base_url}/{endpoint}'
        r = requests.patch(url, headers=self._headers(), json=data, verify=False, timeout=30)
        r.raise_for_status()

    # -------------------------------------------------------------------------
    # Dashboard
    # -------------------------------------------------------------------------

    def get_tickets(self):
        """
        Devuelve la lista de tickets para el dashboard.
        Formato de cada item:
          {id, titulo, cliente, correo, estado, fecha, derivada_calidad}
        """
        result = self._get('gfit_qlt_tickets', params={
            '$select': 'gfit_qlt_ticketid,gfit_name,gfit_correocliente,gfit_estado,createdon',
            '$orderby': 'createdon desc',
        })
        tickets = []
        for t in result.get('value', []):
            tickets.append({
                'id':               t['gfit_qlt_ticketid'],
                'titulo':           t.get('gfit_name', ''),
                'cliente':          t.get('gfit_correocliente', ''),
                'correo':           t.get('gfit_correocliente', ''),
                'estado':           ESTADO_MAP.get(t.get('gfit_estado'), 'Pendiente'),
                'fecha':            (t.get('createdon') or '')[:10],
                'derivada_calidad': False,
            })
        return tickets

    # -------------------------------------------------------------------------
    # Detalle de ticket
    # -------------------------------------------------------------------------

    def get_ticket_detail(self, ticket_id):
        """
        Devuelve el ticket con sus causas agrupadas por gravedad y los productos de cada causa.

        Estructura devuelta:
        {
            'incidencia': {id, titulo, cliente, correo, empresa, idioma, estado, fecha},
            'grupos': [
                {
                    'gravedad': 'Grave',
                    'causas': [
                        {
                            'id': '...',
                            'nombre': '...',
                            'productos': [{nombre, codigo, cantidad, lote, albaran, problema, fecha}]
                        }
                    ]
                },
                ...  # también Moderada y Leve si existen
            ]
        }
        """
        # 1. Ticket
        t = self._get(f'gfit_qlt_tickets({ticket_id})', params={
            '$select': 'gfit_qlt_ticketid,gfit_name,gfit_correocliente,gfit_estado,'
                       'gfit_nombreempresa,gfit_empresa,gfit_idioma,createdon',
        })
        incidencia = {
            'id':      t['gfit_qlt_ticketid'],
            'titulo':  t.get('gfit_name', ''),
            'cliente': t.get('gfit_correocliente', ''),
            'correo':  t.get('gfit_correocliente', ''),
            'empresa': t.get('gfit_nombreempresa', '') or t.get('gfit_empresa', ''),
            'idioma':  t.get('gfit_idioma', ''),
            'estado':  ESTADO_MAP.get(t.get('gfit_estado'), 'Pendiente'),
            'fecha':   (t.get('createdon') or '')[:10],
        }

        # 2. Causas del ticket
        causas_raw = self._get('gfit_qlt_ticket_causes', params={
            '$select': 'gfit_qlt_ticket_causeid,gfit_name',
            '$filter': f"_gfit_qlt_ticketid_value eq {ticket_id}",
        }).get('value', [])

        # 3. Para cada causa obtener sus materiales (con su propia gravedad)
        todos_materiales = []
        for c in causas_raw:
            cause_id   = c['gfit_qlt_ticket_causeid']
            cause_name = c.get('gfit_name', '')
            materiales = self._get('gfit_qlt_ticket_materials', params={
                '$select': 'gfit_qlt_ticket_materialid,gfit_nombreproducto,gfit_codigoproducto,'
                           'gfit_cantidad,gfit_lote,gfit_albaran,gfit_problema,'
                           'gfit_gravedad,gfit_fecharecibimiento',
                '$filter': f"_gfit_qlt_ticket_causeid_value eq {cause_id}",
            }).get('value', [])

            for m in materiales:
                todos_materiales.append({
                    'id':          m['gfit_qlt_ticket_materialid'],
                    'nombre':      m.get('gfit_nombreproducto', ''),
                    'codigo':      m.get('gfit_codigoproducto', ''),
                    'cantidad':    m.get('gfit_cantidad', ''),
                    'lote':        m.get('gfit_lote', ''),
                    'albaran':     m.get('gfit_albaran', ''),
                    'problema':    m.get('gfit_problema', ''),
                    'fecha':       (m.get('gfit_fecharecibimiento') or '')[:10],
                    'gravedad':    GRAVEDAD_MAP.get(m.get('gfit_gravedad'), 'Leve'),
                    'causa_nombre': cause_name,
                    'causa_id':    cause_id,
                })

        # 4. Agrupar por gravedad del MATERIAL (Grave > Moderada > Leve)
        #    Dentro de cada grupo, subagrupamos por causa para dar contexto
        grupos = []
        for gravedad in ['Grave', 'Moderada', 'Leve']:
            mats = [m for m in todos_materiales if m['gravedad'] == gravedad]
            if not mats:
                continue
            # Sub-agrupar por causa
            causas_vistas = {}
            for m in mats:
                cid = m['causa_id']
                if cid not in causas_vistas:
                    causas_vistas[cid] = {'id': cid, 'nombre': m['causa_nombre'], 'productos': []}
                causas_vistas[cid]['productos'].append(m)
            grupos.append({'gravedad': gravedad, 'causas': list(causas_vistas.values())})

        return {'incidencia': incidencia, 'grupos': grupos}

    # -------------------------------------------------------------------------
    # Actualizaciones
    # -------------------------------------------------------------------------

    def update_ticket(self, ticket_id, datos):
        """Actualiza campos de un ticket. datos es un dict con nombres lógicos de Dataverse."""
        self._patch(f'gfit_qlt_tickets({ticket_id})', datos)

    def update_gravedad_material(self, material_id, gravedad_str):
        """Actualiza la gravedad de un material (producto)."""
        code = GRAVEDAD_REVERSE.get(gravedad_str)
        if code is None:
            raise ValueError(f'Gravedad no válida: {gravedad_str}')
        self._patch(f'gfit_qlt_ticket_materials({material_id})', {'gfit_gravedad': code})
