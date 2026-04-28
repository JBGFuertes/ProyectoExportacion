from django.urls import path
from . import views
from comercial.views import actualizar_gravedades

app_name = 'calidad'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('incidencia/<str:incidencia_id>/', views.detalle_incidencia, name='detalle_incidencia'),
    path('incidencia/<str:incidencia_id>/guardar/', actualizar_gravedades, name='actualizar_gravedades'),
    path('generar-respuesta/', views.generar_respuesta, name='generar_respuesta'),
]
