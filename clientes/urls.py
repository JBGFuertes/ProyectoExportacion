from django.urls import path
from . import views

app_name = 'clientes'

urlpatterns = [
    path('', views.portal, name='portal'),
    path('nueva-incidencia/', views.nueva_incidencia, name='nueva_incidencia'),
    path('mis-incidencias/', views.mis_incidencias, name='mis_incidencias'),
]
