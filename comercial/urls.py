from django.urls import path
from . import views

app_name = 'comercial'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('ajustar-tono/', views.ajustar_tono, name='ajustar_tono'),
    path('incidencia/<str:incidencia_id>/', views.detalle_incidencia, name='detalle_incidencia'),
    path('incidencia/<str:incidencia_id>/gravedades/', views.actualizar_gravedades, name='actualizar_gravedades'),
    path('incidencia/<str:incidencia_id>/derivar-calidad/', views.derivar_calidad, name='derivar_calidad'),
    path('material/<str:material_id>/derivar-calidad/', views.derivar_material_calidad, name='derivar_material_calidad'),
    path('incidencia/<str:incidencia_id>/enviar-respuesta/', views.enviar_respuesta, name='enviar_respuesta'),
    path('incidencia/<str:incidencia_id>/finalizar/', views.marcar_finalizada, name='marcar_finalizada'),
]
