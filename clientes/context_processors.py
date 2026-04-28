from .i18n import UI, SUPPORTED


def clientes_i18n(request):
    lang = request.session.get('clientes_lang', 'es')
    if lang not in SUPPORTED:
        lang = 'es'
    return {'t': UI[lang], 'lang': lang}
