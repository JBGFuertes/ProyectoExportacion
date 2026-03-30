"""
Cliente para la API de Microsoft Dataverse.
Toda la lógica de conexión y consultas está aquí.
Para cambiar de fuente de datos en el futuro, solo hay que modificar este fichero.
"""
import requests


class DataverseClient:
    def __init__(self, url, token):
        self.base_url = url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {token}',
            'OData-MaxVersion': '4.0',
            'OData-Version': '4.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }

    def get_incidencias(self, filtro=None):
        """Obtiene la lista de incidencias desde Dataverse."""
        # TODO: implementar con el nombre real de la entidad en tu Dataverse
        raise NotImplementedError

    def get_incidencia(self, incidencia_id):
        """Obtiene el detalle de una incidencia."""
        raise NotImplementedError

    def update_incidencia(self, incidencia_id, datos):
        """Actualiza campos de una incidencia."""
        raise NotImplementedError

    def get_historial_cliente(self, cliente_id):
        """Obtiene el historial de incidencias de un cliente."""
        raise NotImplementedError
