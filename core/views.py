from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def dashboard_view(request):
    # Você pode adicionar lógica aqui para mostrar diferentes coisas no dashboard
    # com base no grupo do request.user, por exemplo:
    # if request.user.groups.filter(name='Operador').exists():
    #    # contexto específico do operador
    # elif request.user.groups.filter(name='Supervisor').exists():
    #    # contexto específico do supervisor
    context = {
        'page_title': 'Dashboard Principal'
    }
    return render(request, 'core/dashboard.html', context)