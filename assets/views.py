# assets/views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Computador, ChamadoManutencao
# Se você criou um formulário Django para ChamadoManutencao, importe-o aqui

# TODO: Adicionar view para detalhes do computador (AJAX)
from django.template.loader import render_to_string # Para renderizar um template parcial

# TODO: Adicionar view para ping (AJAX)
import subprocess # Para executar o comando ping
import platform   # Para ajustar o comando ping conforme o SO
from django.views.decorators.http import require_POST, require_GET # require_GET para o ping
from django.utils import timezone # Para atualizar ultimo_ping_status
from .utils import executar_ping

import json

@login_required
def layout_maquinas_view(request):
    computadores = Computador.objects.all().order_by('nome_host')
    context = {
        'computadores': computadores,
        'page_title': 'Layout de Máquinas'
    }
    return render(request, 'assets/layout_maquinas.html', context)

@login_required
@require_POST # Garante que esta view só pode ser acessada via método POST
def reportar_problema_view(request):
    if request.method == 'POST':
        try:
            computador_id = request.POST.get('computador_id')
            titulo = request.POST.get('titulo')
            descricao_problema = request.POST.get('descricao_problema')

            if not all([computador_id, titulo, descricao_problema]):
                return JsonResponse({'success': False, 'error': 'Dados incompletos.'}, status=400)

            computador = get_object_or_404(Computador, id=computador_id)

            # Cria o chamado
            chamado = ChamadoManutencao.objects.create(
                computador=computador,
                titulo=titulo,
                descricao_problema=descricao_problema,
                aberto_por=request.user # Associa o usuário logado como quem abriu
            )

            # Atualiza o status do computador
            computador.status_reportado = 'problema'
            computador.save()

            return JsonResponse({
                'success': True,
                'message': 'Chamado aberto com sucesso!',
                'chamado_id': chamado.id,
                'novo_status_computador': computador.get_status_reportado_display(),
                'novo_status_class': 'status-problema', # Para atualizar a classe CSS no frontend
                'computador_id': computador.id
            })
        except Computador.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Computador não encontrado.'}, status=404)
        except Exception as e:
            # Logar o erro e.g., logger.error(f"Erro ao reportar problema: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Método não permitido.'}, status=405)

# TODO: Adicionar view para detalhes do computador (AJAX)



# ... (outras views: layout_maquinas_view, reportar_problema_view, ping_computador_view) ...

@login_required
@require_GET # Estamos apenas buscando dados
def detalhes_computador_view(request, comp_id):
    computador = get_object_or_404(Computador, id=comp_id)
    chamados = ChamadoManutencao.objects.filter(computador=computador).order_by('-data_abertura')

    # Renderiza um template HTML parcial com os detalhes
    # Isso é útil para injetar diretamente no modal via JavaScript
    context = {
        'computador': computador,
        'chamados': chamados
    }
    # Opcional: Se quiser retornar JSON e construir o HTML no JS:
    # data = {
    #     'computador': {
    #         'nome_host': computador.nome_host,
    #         'setor': computador.setor,
    #         'ip': computador.ip_associado.address if computador.ip_associado else "N/A",
    #         'status_reportado': computador.get_status_reportado_display(),
    #         'status_rede': computador.get_status_rede_display()
    #     },
    #     'chamados': list(chamados.values('id', 'titulo', 'status_chamado', 'data_abertura'))
    # }
    # return JsonResponse(data)

    # Retornando HTML parcial:
    html_content = render_to_string('assets/partials/detalhes_computador_modal_content.html', context, request=request)
    return JsonResponse({'success': True, 'html_content': html_content})

# -----------       View no Django para Atualizar o Chamado   ---------------------

@login_required
@require_POST
def atualizar_chamado_view(request):
    chamado_id = request.POST.get('chamado_id')
    novo_status = request.POST.get('status_chamado')
    solucao = request.POST.get('solucao_aplicada', '') # Default para string vazia se não vier

    if not chamado_id or not novo_status:
        return JsonResponse({'success': False, 'error': 'Dados incompletos.'}, status=400)

    try:
        chamado = get_object_or_404(ChamadoManutencao, id=chamado_id)

        # Lógica de permissão (exemplo simples: só o técnico responsável ou admin/staff pode mudar)
        # if not (request.user == chamado.tecnico_responsavel or request.user.is_staff):
        #     return JsonResponse({'success': False, 'error': 'Você não tem permissão para atualizar este chamado.'}, status=403)

        chamado.status_chamado = novo_status
        chamado.solucao_aplicada = solucao

        if novo_status in ['resolvido', 'fechado'] and not chamado.data_resolucao:
            chamado.data_resolucao = timezone.now()
        elif novo_status not in ['resolvido', 'fechado']:
            chamado.data_resolucao = None # Limpa data de resolução se for reaberto

        # Atribuir técnico se ainda não tiver e o usuário logado for staff/helpdesk
        # (Lógica de perfil aqui seria útil)
        if not chamado.tecnico_responsavel and request.user.is_staff: # Exemplo
             chamado.tecnico_responsavel = request.user

        chamado.save() # Isso vai disparar a lógica no método save() do ChamadoManutencao
                       # para atualizar o status do computador se necessário.

        # Precisamos do status atualizado do computador para enviar de volta
        computador_status_reportado = chamado.computador.get_status_reportado_display()
        computador_status_reportado_class = 'status-ok' # default
        if chamado.computador.status_reportado == 'problema':
            computador_status_reportado_class = 'status-problema'
        elif chamado.computador.status_reportado == 'manutencao':
            computador_status_reportado_class = 'status-manutencao'


        return JsonResponse({
            'success': True,
            'message': 'Chamado atualizado com sucesso!',
            'chamado_id': chamado.id,
            'novo_status_chamado_display': chamado.get_status_chamado_display(),
            'computador_id': chamado.computador.id,
            'computador_status_reportado_display': computador_status_reportado,
            'computador_status_reportado_class': computador_status_reportado_class,
            'html_chamados_atualizado': render_to_string( # Para atualizar a lista de chamados no modal
                'assets/partials/lista_chamados_para_modal.html', # NOVO TEMPLATE PARCIAL SÓ PARA A LISTA
                {'chamados': ChamadoManutencao.objects.filter(computador=chamado.computador).order_by('-data_abertura')}
            ),
            'html_form_chamado_atualizado': render_to_string( # Para atualizar o formulário no modal
                 'assets/partials/form_atualizar_chamado_para_modal.html',
                 {'ultimo_chamado': ChamadoManutencao.objects.filter(computador=chamado.computador, status_chamado__in=['aberto', 'em_atendimento', 'aguardando_peca']).order_by('-data_abertura').first(),
                  'computador': chamado.computador} # NOVO TEMPLATE PARCIAL SÓ PARA O FORM
            )
        })
    except ChamadoManutencao.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Chamado não encontrado.'}, status=404)
    except Exception as e:
        # logger.error(f"Erro ao atualizar chamado: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# TODO: Adicionar view para ping (AJAX)


# ... (outras views) ...

@login_required
@require_GET
def ping_computador_view(request, comp_id):
    computador = get_object_or_404(Computador, id=comp_id)
    ip_address_obj = computador.ip_associado

    status_text_map = {
        'online': 'Online',
        'offline': 'Offline',
        'unreachable': 'Inalcançável',
        'timeout': 'Timeout',
        'error_ping': 'Erro Ping',
        'error_ping_cmd_not_found': 'Erro Comando Ping',
        'no_ip': 'Sem IP'
    }
    status_class_map = {
        'online': 'bg-success',
        'offline': 'bg-danger',
        'unreachable': 'bg-warning',
        'timeout': 'bg-warning',
        'error_ping': 'bg-dark',
        'error_ping_cmd_not_found': 'bg-dark',
        'no_ip': 'bg-secondary'
    }

    if ip_address_obj:
        ip_to_ping = ip_address_obj.address
        online_status = executar_ping(ip_to_ping) # <<< USA A NOVA FUNÇÃO

        # Atualiza o modelo
        computador.status_rede = online_status
        computador.ultimo_ping_status = timezone.now()
        computador.save(update_fields=['status_rede', 'ultimo_ping_status'])
    else:
        online_status = 'no_ip'
        ip_to_ping = None # Definir para evitar erro no JsonResponse

    return JsonResponse({
        'success': True,
        'online_status': online_status,
        'status_text': status_text_map.get(online_status, 'Desconhecido'),
        'status_class': status_class_map.get(online_status, 'bg-light text-dark'),
        'computador_id': computador.id,
        'ip_pingado': ip_to_ping
    })


@login_required
# @user_passes_test(is_admin_or_editor) # No futuro, adicionar verificação de permissão
@require_POST  # Esta view só deve aceitar POST
def update_computador_position_view(request, comp_id):
    if not request.user.is_staff:  # Exemplo simples de permissão: só staff pode editar
        return JsonResponse({'success': False, 'error': 'Permissão negada.'}, status=403)
    try:
        computador = get_object_or_404(Computador, id=comp_id)
        data = json.loads(request.body)  # Pega dados do corpo JSON da requisição

        new_pos_x = data.get('pos_x')
        new_pos_y = data.get('pos_y')

        if new_pos_x is not None and new_pos_y is not None:
            try:
                computador.pos_x = int(new_pos_x)
                computador.pos_y = int(new_pos_y)
                computador.save(update_fields=['pos_x', 'pos_y'])
                return JsonResponse({'success': True, 'message': 'Posição atualizada com sucesso.'})
            except ValueError:
                return JsonResponse({'success': False, 'error': 'Valores de posição inválidos.'}, status=400)
        else:
            return JsonResponse({'success': False, 'error': 'Dados de posição ausentes.'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Payload JSON inválido.'}, status=400)
    except Computador.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Computador não encontrado.'}, status=404)
    except Exception as e:
        # logger.error(f"Erro ao atualizar posição do computador {comp_id}: {e}")
        return JsonResponse({'success': False, 'error': f'Erro interno do servidor: {str(e)}'}, status=500)