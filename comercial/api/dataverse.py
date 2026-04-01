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

    def update_gravedades_productos(self, incidencia_id, productos):
        """
        Actualiza la gravedad de los productos de una incidencia.

        :param incidencia_id: ID de la incidencia en Dataverse
        :param productos: lista de dicts con {'codigo': str, 'gravedad': str}
        """
        # TODO: implementar con el nombre real de la entidad y columnas de Dataverse
        # Ejemplo orientativo:
        # for p in productos:
        #     product_record_id = self._buscar_producto(incidencia_id, p['codigo'])
        #     self._patch(f"/cr_productos({product_record_id})", {"cr_gravedad": p['gravedad']})
        raise NotImplementedError
