from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    # Outras URLs do app 'core' podem vir aqui
]