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

IDIOMA_MAP = {
    347780000: 'Español',
    347780001: 'Inglés',
    347780002: 'Francés',
    347780003: 'Portugués',
    347780004: 'Alemán',
    347780005: 'Italiano',
}


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

    def _get(self, endpoint, params=None, extra_headers=None):
        url = f'{self.base_url}/{endpoint}'
        headers = self._headers()
        if extra_headers:
            headers.update(extra_headers)
        r = requests.get(url, headers=headers, params=params, verify=False, timeout=30)
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
        result = self._get('gfit_qlt_tickets', params={
            '$select': 'gfit_qlt_ticketid,gfit_name,gfit_correocliente,gfit_estado,createdon,gfit_derivadacalidad',
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
                'derivada_calidad': bool(t.get('gfit_derivadacalidad', False)),
            })
        return tickets

    def get_tickets_calidad(self):
        result = self._get('gfit_qlt_tickets', params={
            '$select': 'gfit_qlt_ticketid,gfit_name,gfit_correocliente,gfit_estado,createdon',
            '$filter': 'gfit_derivadacalidad eq true',
            '$orderby': 'createdon desc',
        })
        tickets = []
        for t in result.get('value', []):
            tickets.append({
                'id':     t['gfit_qlt_ticketid'],
                'titulo': t.get('gfit_name', ''),
                'cliente': t.get('gfit_correocliente', ''),
                'correo': t.get('gfit_correocliente', ''),
                'estado': ESTADO_MAP.get(t.get('gfit_estado'), 'Pendiente'),
                'fecha':  (t.get('createdon') or '')[:10],
            })
        return tickets

    # -------------------------------------------------------------------------
    # Detalle de ticket
    # -------------------------------------------------------------------------

    def get_ticket_detail(self, ticket_id):
        # 1. Ticket
        t = self._get(f'gfit_qlt_tickets({ticket_id})', params={
            '$select': 'gfit_qlt_ticketid,gfit_name,gfit_correocliente,gfit_estado,'
                       'gfit_nombreempresa,gfit_empresa,gfit_idioma,createdon,'
                       'gfit_conversationid,gfit_messageid',
        })
        incidencia = {
            'id':              t['gfit_qlt_ticketid'],
            'titulo':          t.get('gfit_name', ''),
            'cliente':         t.get('gfit_correocliente', ''),
            'correo':          t.get('gfit_correocliente', ''),
            'empresa':         t.get('gfit_nombreempresa', '') or t.get('gfit_empresa', ''),
            'idioma':          IDIOMA_MAP.get(t.get('gfit_idioma'), ''),
            'estado':          ESTADO_MAP.get(t.get('gfit_estado'), 'Pendiente'),
            'fecha':           (t.get('createdon') or '')[:10],
            'conversation_id': t.get('gfit_conversationid', ''),
            'message_id':      t.get('gfit_messageid', ''),
        }

        # 2. Causas del ticket
        causas_raw = self._get('gfit_qlt_ticket_causes', params={
            '$select': 'gfit_qlt_ticket_causeid,gfit_name,_gfit_qlt_cause_catalogid_value',
            '$filter': f"_gfit_qlt_ticketid_value eq {ticket_id}",
        }).get('value', [])

        # 3. Para cada causa obtener sus materiales
        todos_materiales = []
        for c in causas_raw:
            cause_id         = c['gfit_qlt_ticket_causeid']
            cause_name       = c.get('gfit_name', '')
            cause_catalog_id = c.get('_gfit_qlt_cause_catalogid_value') or ''
            materiales = self._get('gfit_qlt_ticket_materials', params={
                '$select': 'gfit_qlt_ticket_materialid,gfit_nombreproducto,gfit_codigoproducto,'
                           'gfit_cantidad,gfit_cantidadtotal,gfit_lote,gfit_albaran,gfit_problema,'
                           'gfit_gravedad,gfit_fecharecibimiento,gfit_derivadacalidad,gfit_respondido',
                '$filter': f"_gfit_qlt_ticket_causeid_value eq {cause_id}",
            }).get('value', [])

            for m in materiales:
                todos_materiales.append({
                    'id':              m['gfit_qlt_ticket_materialid'],
                    'nombre':          m.get('gfit_nombreproducto', ''),
                    'codigo':          m.get('gfit_codigoproducto', ''),
                    'cantidad':        m.get('gfit_cantidad', ''),
                    'cantidad_total':  m.get('gfit_cantidadtotal', ''),
                    'lote':            m.get('gfit_lote', ''),
                    'albaran':         m.get('gfit_albaran', ''),
                    'problema':        m.get('gfit_problema', ''),
                    'fecha':           (m.get('gfit_fecharecibimiento') or '')[:10],
                    'gravedad':        GRAVEDAD_MAP.get(m.get('gfit_gravedad'), 'Leve'),
                    'causa_nombre':    cause_name,
                    'causa_id':        cause_id,
                    'causa_catalog_id': cause_catalog_id,
                    'derivada_calidad': bool(m.get('gfit_derivadacalidad', False)),
                    'respondido':       bool(m.get('gfit_respondido', False)),
                })

        # 4. Agrupar por causa específica; dentro de cada causa, subgrupos por gravedad
        causas_vistas = {}
        for m in todos_materiales:
            cid = m['causa_id']
            if cid not in causas_vistas:
                causas_vistas[cid] = {
                    'causa_id':         cid,
                    'causa_nombre':     m['causa_nombre'],
                    'causa_catalog_id': m['causa_catalog_id'],
                    'subgrupos':        {},
                }
            grav = m['gravedad']
            if grav not in causas_vistas[cid]['subgrupos']:
                causas_vistas[cid]['subgrupos'][grav] = []
            causas_vistas[cid]['subgrupos'][grav].append(m)

        grupos = []
        for causa in causas_vistas.values():
            cid = causa['causa_id']
            subgrupos = [
                {
                    'gravedad':  grav,
                    'productos': causa['subgrupos'][grav],
                    'sg_key':    f"{cid[:8]}-{grav.lower()}",
                }
                for grav in ['Grave', 'Moderada', 'Leve']
                if grav in causa['subgrupos']
            ]
            grupos.append({
                'causa_id':         cid,
                'causa_nombre':     causa['causa_nombre'],
                'causa_catalog_id': causa['causa_catalog_id'],
                'subgrupos':        subgrupos,
            })

        # Mapa nombre → id de TODAS las ticket_causes (incluso las sin materiales)
        all_ticket_causes = {c.get('gfit_name', ''): c['gfit_qlt_ticket_causeid'] for c in causas_raw}

        return {'incidencia': incidencia, 'grupos': grupos, 'all_ticket_causes': all_ticket_causes}

    # -------------------------------------------------------------------------
    # Catálogo de causas
    # -------------------------------------------------------------------------

    def get_causes_catalog(self):
        result = self._get('gfit_qlt_cause_catalogs', params={
            '$select': 'gfit_qlt_cause_catalogid,gfit_nombrecausa,gfit_gravedad,gfit_orden,'
                       'gfit_causageneral,gfit_causageneral_en',
            '$filter': 'gfit_activo eq true',
            '$orderby': 'gfit_orden asc',
        }, extra_headers={
            'Prefer': 'odata.include-annotations="OData.Community.Display.V1.FormattedValue"',
        })
        causas = []
        for c in result.get('value', []):
            causas.append({
                'id':              c['gfit_qlt_cause_catalogid'],
                'nombre':          c.get('gfit_nombrecausa', ''),
                'causageneral':    c.get('gfit_causageneral@OData.Community.Display.V1.FormattedValue', '')
                                   or c.get('gfit_causageneral', ''),
                'causageneral_en': c.get('gfit_causageneral_en@OData.Community.Display.V1.FormattedValue', '')
                                   or c.get('gfit_causageneral_en', ''),
                'gravedad':        GRAVEDAD_MAP.get(c.get('gfit_gravedad'), 'Leve'),
                'gravedad_code':   c.get('gfit_gravedad', 347780000),
            })
        return causas

    # -------------------------------------------------------------------------
    # Actualizaciones
    # -------------------------------------------------------------------------

    def get_ticket_reply_data(self, ticket_id):
        """Devuelve los datos mínimos necesarios para responder al email de la incidencia."""
        t = self._get(f'gfit_qlt_tickets({ticket_id})', params={
            '$select': 'gfit_correocliente,gfit_conversationid,gfit_messageid',
        })
        return {
            'destinatario':    t.get('gfit_correocliente', ''),
            'conversation_id': t.get('gfit_conversationid', ''),
            'message_id':      t.get('gfit_messageid', ''),
        }

    def update_ticket(self, ticket_id, datos):
        self._patch(f'gfit_qlt_tickets({ticket_id})', datos)

    def update_gravedad_material(self, material_id, gravedad_str):
        code = GRAVEDAD_REVERSE.get(gravedad_str)
        if code is None:
            raise ValueError(f'Gravedad no válida: {gravedad_str}')
        self._patch(f'gfit_qlt_ticket_materials({material_id})', {'gfit_gravedad': code})

    def delete_ticket_cause_if_empty(self, cause_id):
        """Borra la ticket_cause si ya no tiene materiales."""
        materiales = self._get('gfit_qlt_ticket_materials', params={
            '$select': 'gfit_qlt_ticket_materialid',
            '$filter': f"_gfit_qlt_ticket_causeid_value eq {cause_id}",
            '$top': '1',
        }).get('value', [])
        if not materiales:
            url = f'{self.base_url}/gfit_qlt_ticket_causes({cause_id})'
            requests.delete(url, headers=self._headers(), verify=False, timeout=30).raise_for_status()

    def create_ticket_cause(self, ticket_id, nombre, catalog_cause_id=None):
        """Crea una nueva causa en el ticket y devuelve su ID."""
        payload = {
            'gfit_name': nombre,
            'gfit_qlt_ticketID@odata.bind': f'/gfit_qlt_tickets({ticket_id})',
        }
        if catalog_cause_id:
            payload['gfit_qlt_cause_catalogID@odata.bind'] = f'/gfit_qlt_cause_catalogs({catalog_cause_id})'
        r = requests.post(
            f'{self.base_url}/gfit_qlt_ticket_causes',
            headers=self._headers(),
            json=payload,
            verify=False,
            timeout=30,
        )
        if not r.ok:
            raise Exception(f'Dataverse {r.status_code} al crear causa: {r.text}')
        location = r.headers.get('OData-EntityId', '') or r.headers.get('Location', '')
        return location.split('(')[-1].rstrip(')')

    def update_material(self, material_id, gravedad_str, causa_id=None, problema=None):
        """Actualiza gravedad y opcionalmente la causa y el problema de un material."""
        code = GRAVEDAD_REVERSE.get(gravedad_str)
        if code is None:
            raise ValueError(f'Gravedad no válida: {gravedad_str}')
        data = {'gfit_gravedad': code}
        if causa_id:
            data['gfit_qlt_ticket_causeID@odata.bind'] = f'/gfit_qlt_ticket_causes({causa_id})'
        if problema is not None:
            data['gfit_problema'] = problema
        self._patch(f'gfit_qlt_ticket_materials({material_id})', data)

    # -------------------------------------------------------------------------
    # Derivar a Calidad (nivel material y ticket)
    # -------------------------------------------------------------------------

    def marcar_materiales_respondidos(self, material_ids: list):
        for material_id in material_ids:
            self._patch(f'gfit_qlt_ticket_materials({material_id})', {'gfit_respondido': True})

    def derivar_material(self, material_id, derivar: bool):
        self._patch(f'gfit_qlt_ticket_materials({material_id})', {'gfit_derivadacalidad': derivar})

    def derivar_ticket(self, ticket_id, derivar: bool):
        self._patch(f'gfit_qlt_tickets({ticket_id})', {'gfit_derivadacalidad': derivar})

    def has_derived_materials(self, ticket_id):
        """Devuelve True si el ticket tiene al menos un material derivado a calidad."""
        causes = self._get('gfit_qlt_ticket_causes', params={
            '$select': 'gfit_qlt_ticket_causeid',
            '$filter': f"_gfit_qlt_ticketid_value eq {ticket_id}",
        }).get('value', [])
        if not causes:
            return False
        cause_ids = [c['gfit_qlt_ticket_causeid'] for c in causes]
        cause_filter = ' or '.join(
            f"_gfit_qlt_ticket_causeid_value eq {cid}" for cid in cause_ids
        )
        materials = self._get('gfit_qlt_ticket_materials', params={
            '$select': 'gfit_qlt_ticket_materialid',
            '$filter': f"({cause_filter}) and gfit_derivadacalidad eq true",
            '$top': '1',
        }).get('value', [])
        return len(materials) > 0

    def get_ticket_detail_calidad(self, ticket_id):
        """Igual que get_ticket_detail pero solo devuelve materiales derivados a calidad."""
        detail = self.get_ticket_detail(ticket_id)
        filtered_grupos = []
        for grupo in detail.get('grupos', []):
            filtered_subgrupos = []
            for subgrupo in grupo['subgrupos']:
                prods = [p for p in subgrupo['productos'] if p.get('derivada_calidad')]
                if prods:
                    filtered_subgrupos.append({**subgrupo, 'productos': prods})
            if filtered_subgrupos:
                filtered_grupos.append({**grupo, 'subgrupos': filtered_subgrupos})
        return {
            'incidencia':       detail['incidencia'],
            'grupos':           filtered_grupos,
            'all_ticket_causes': detail.get('all_ticket_causes', {}),
        }
