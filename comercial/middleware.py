class ComercialMiddleware:
    """
    Middleware personalizado para la app comercial.
    Aquí se puede añadir lógica que se ejecute en cada request/response.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Lógica antes de la vista (ej: comprobar sesión activa)
        response = self.get_response(request)
        # Lógica después de la vista
        return response
