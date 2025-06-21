# dimensionamento/urls.py
from django.urls import path
from . import views

app_name = 'dimensionamento'

urlpatterns = [
    path('cenarios/novo/', views.criar_editar_cenario_view, name='criar_cenario'),
    path('cenarios/<int:cenario_id>/editar/', views.criar_editar_cenario_view, name='editar_cenario'),
    path('cenarios/<int:cenario_id>/resultados/', views.resultados_cenario_view, name='resultados_cenario'),
    # Futura lista de cenários:
    path('cenarios/', views.listar_cenarios_view, name='lista_cenarios'),
]