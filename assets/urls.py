from django.urls import path
from . import views

app_name = 'assets' # Namespace para as URLs deste app

urlpatterns = [
    path('layout/', views.layout_maquinas_view, name='layout_maquinas'),
    path('reportar-problema/', views.reportar_problema_view, name='reportar_problema'),
    path('computador/<int:comp_id>/ping/', views.ping_computador_view, name='ping_computador'),
    path('computador/<int:comp_id>/detalhes/', views.detalhes_computador_view, name='detalhes_computador'),
    path('chamado/atualizar/', views.atualizar_chamado_view, name='atualizar_chamado'),
    path('computador/<int:comp_id>/update-position/', views.update_computador_position_view, name='update_computador_position'),  # <<< NOVA URL
    path('chamados/', views.lista_chamados_view, name='lista_chamados'), # <<<< VERIFIQUE ESTE NOME
    path('chamados/<int:chamado_id>/editar/', views.editar_chamado_view, name='editar_chamado'),
    path('computadores/', views.lista_computadores_view, name='lista_computadores'),
    path('computadores/importar/', views.importar_computadores_view, name='importar_computadores_csv_ui'),

]