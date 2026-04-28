SUPPORTED = frozenset({'es', 'en'})

UI = {
    'es': {
        'html_lang':       'es',
        'navbar_brand':    'Portal de Clientes',
        'navbar_new':      'Nueva incidencia',
        'navbar_mine':     'Mis incidencias',
        'page_title':      'Nueva Incidencia',
        'section_id':      'Identificación',
        'label_company':   'Nombre de su empresa',
        'label_email':     'Correo electrónico',
        'section_products':'Productos afectados',
        'btn_add_product': 'Añadir producto',
        'label_code':      'Código producto',
        'label_product':   'Producto',
        'label_lot':       'Lote',
        'label_qty':       'Cantidad afectada',
        'label_note':      'Albarán',
        'label_date':      'Fecha de recibimiento',
        'label_problem':   'Problema',
        'ph_problem':      'Describe brevemente el problema',
        'label_cause':     'Causa',
        'cause_ph':        '-- Selecciona causa --',
        'btn_submit':      'Enviar incidencia',
        'btn_cancel':      'Cancelar',
        'product_n':       'Producto',
        'success_title':   'Incidencia registrada',
        'success_msg':     'Hemos recibido tu incidencia. En breve nos pondremos en contacto contigo.',
        'btn_another':     'Registrar otra',
        'btn_view_mine':   'Ver mis incidencias',
        'err_fields':      'Los campos Empresa y Correo son obligatorios.',
        'err_products':    'Añade al menos un producto.',
    },
    'en': {
        'html_lang':       'en',
        'navbar_brand':    'Customer Portal',
        'navbar_new':      'New claim',
        'navbar_mine':     'My claims',
        'page_title':      'New Claim',
        'section_id':      'Identification',
        'label_company':   'Company name',
        'label_email':     'Email address',
        'section_products':'Affected products',
        'btn_add_product': 'Add product',
        'label_code':      'Product code',
        'label_product':   'Product',
        'label_lot':       'Batch',
        'label_qty':       'Affected quantity',
        'label_note':      'Delivery note',
        'label_date':      'Date of receipt',
        'label_problem':   'Problem',
        'ph_problem':      'Briefly describe the problem',
        'label_cause':     'Cause',
        'cause_ph':        '-- Select cause --',
        'btn_submit':      'Submit claim',
        'btn_cancel':      'Cancel',
        'product_n':       'Product',
        'success_title':   'Claim registered',
        'success_msg':     'We have received your claim. We will contact you shortly.',
        'btn_another':     'Register another',
        'btn_view_mine':   'View my claims',
        'err_fields':      'Company and Email fields are required.',
        'err_products':    'Please add at least one product.',
    },
}


def get_lang(request):
    """Lee ?lang= de la URL, lo persiste en sesión y lo devuelve. Fallback: 'es'."""
    param = request.GET.get('lang', '').lower()
    if param in SUPPORTED:
        request.session['clientes_lang'] = param
        return param
    stored = request.session.get('clientes_lang', 'es')
    return stored if stored in SUPPORTED else 'es'
