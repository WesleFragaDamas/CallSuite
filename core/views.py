from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required # Garante que apenas usuários logados acessem
def dashboard_view(request):
    return render(request, 'core/dashboard.html')

# Não precisamos de uma view para login/logout aqui,
# pois estamos usando as views embutidas do Django.
# A view de login padrão do Django renderizará 'registration/login.html'