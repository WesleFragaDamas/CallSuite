# assets/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from .models import Computador, ChamadoManutencao, IPAddress
# Se você criou um formulário Django para ChamadoManutencao, importe-o aqui

# TODO: Adicionar view para detalhes do computador (AJAX)
from django.template.loader import render_to_string # Para renderizar um template parcial

# TODO: Adicionar view para ping (AJAX)
import subprocess # Para executar o comando ping
import platform   # Para ajustar o comando ping conforme o SO
from django.views.decorators.http import require_POST, require_GET # require_GET para o ping
from django.utils import timezone # Para atualizar ultimo_ping_status
from .utils import executar_ping

# TODO: Importar arquvivo CSV
from .forms import CSVImportForm # Importe o formulário de upload
from .utils import processar_csv_computadores # Importe a função de processamento

import json

# NOVOS IMPORTS PARA PERMISSÕES
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied # Para levantar 403 manualmente se necessário

from .forms import ChamadoManutencaoUpdateForm # Importe o novo formulário
from django.contrib import messages # Para mensagens de feedback

@login_required
@permission_required('assets.view_computador', raise_exception=True)
def layout_maquinas_view(request):
    computadores = Computador.objects.all().order_by('nome_host')
    # No futuro, podemos passar as dimensões do layout aqui se LayoutConfig for implementado
    # layout_config = LayoutConfig.objects.filter(ativo=True).first()
    context = {
        'computadores': computadores,
        'page_title': 'Layout de Máquinas',
        # 'layout_config': layout_config
    }
    return render(request, 'assets/layout_maquinas.html', context)

@login_required
@permission_required('assets.add_chamadomanutencao', raise_exception=True)
@require_POST
def reportar_problema_view(request):
    try:
        computador_id = request.POST.get('computador_id')
        titulo = request.POST.get('titulo')
        descricao_problema = request.POST.get('descricao_problema')

        if not all([computador_id, titulo, descricao_problema]):
            return JsonResponse({'success': False, 'error': 'Dados incompletos.'}, status=400)

        computador = get_object_or_404(Computador, id=computador_id)
        chamado = ChamadoManutencao.objects.create(
            computador=computador,
            titulo=titulo,
            descricao_problema=descricao_problema,
            aberto_por=request.user
        )
        computador.status_reportado = 'problema'
        computador.save()

        return JsonResponse({
            'success': True,
            'message': 'Chamado aberto com sucesso!',
            'chamado_id': chamado.id,
            'novo_status_class': 'status-problema',
            'novo_status_computador': computador.get_status_reportado_display(),
            'computador_id': computador.id
        })
    except Computador.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Computador não encontrado.'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# TODO: Adicionar view para detalhes do computador (AJAX)

@login_required
@permission_required('assets.view_chamadomanutencao', raise_exception=True)  # Quem pode ver chamados
def lista_chamados_view(request):
    # Definir quais chamados mostrar: todos, apenas abertos, atribuídos ao usuário, etc.
    # Começaremos mostrando os mais recentes que não estão fechados/resolvidos.
    lista_de_chamados = ChamadoManutencao.objects.exclude(
        status_chamado__in=['resolvido', 'fechado']
    ).order_by('-data_abertura')

    # TODO: Adicionar filtros (por status, por técnico, por data, etc.) no futuro
    # TODO: Adicionar paginação se a lista for muito grande

    context = {
        'chamados': lista_de_chamados,
        'page_title': 'Lista de Chamados Ativos'
    }
    return render(request, 'assets/lista_chamados.html', context)

# ... (outras views: layout_maquinas_view, reportar_problema_view, ping_computador_view) ...

@login_required
@permission_required('assets.view_chamadomanutencao', raise_exception=True)
@require_GET
def detalhes_computador_view(request, comp_id):
    computador = get_object_or_404(Computador, id=comp_id)
    chamados = ChamadoManutencao.objects.filter(computador=computador).order_by('-data_abertura')

    # Identifica o último chamado válido para ação para o formulário
    ultimo_chamado_para_acao = chamados.filter(
        status_chamado__in=['aberto', 'em_atendimento', 'aguardando_peca']
    ).first() # .first() já pega o mais recente devido ao order_by em 'chamados'

    context = {
        'computador': computador,
        'chamados': chamados,
        'ultimo_chamado_valido_para_acao': ultimo_chamado_para_acao,
        # 'user': request.user, (O Django já adiciona 'user' e 'perms' ao contexto com RequestContext,
        #                      que é usado por render_to_string por padrão se request é passado)
    }
    html_content = render_to_string('assets/partials/detalhes_computador_modal_content.html', context, request=request)
    return JsonResponse({'success': True, 'html_content': html_content})


# -----------       View no Django para Atualizar o Chamado   ---------------------

@login_required
@permission_required('assets.change_chamadomanutencao', raise_exception=True)
@require_POST
def atualizar_chamado_view(request):
    # ... (corpo da função como antes) ...
    # COPIE O CORPO COMPLETO DESTA FUNÇÃO DA SUA VERSÃO FUNCIONAL ANTERIOR
    # Certifique-se de que ela usa render_to_string para os parciais de HTML se necessário.
    try:
        chamado_id = request.POST.get('chamado_id')
        novo_status = request.POST.get('status_chamado')
        solucao = request.POST.get('solucao_aplicada', '')
        chamado = get_object_or_404(ChamadoManutencao, id=chamado_id)

        # Lógica de permissão mais fina pode ser adicionada aqui se necessário
        # ex: if request.user != chamado.tecnico_responsavel and not request.user.is_staff: ...

        chamado.status_chamado = novo_status
        chamado.solucao_aplicada = solucao
        if novo_status in ['resolvido', 'fechado'] and not chamado.data_resolucao:
            chamado.data_resolucao = timezone.now()
        elif novo_status not in ['resolvido', 'fechado']:
            chamado.data_resolucao = None

        if not chamado.tecnico_responsavel and (
                request.user.is_staff or request.user.groups.filter(name__in=['Helpdesk', 'Admin']).exists()):
            chamado.tecnico_responsavel = request.user

        chamado.save()  # Dispara a lógica no model para atualizar o status do computador

        from django.template.loader import render_to_string  # Mova para o topo do arquivo se usado em múltiplas views
        computador = chamado.computador  # Pega o computador do chamado atualizado

        proximo_chamado_para_acao = ChamadoManutencao.objects.filter(
            computador=computador,
            status_chamado__in=['aberto', 'em_atendimento', 'aguardando_peca']  # Status que permitem ação
        ).order_by('-data_abertura').first()


        status_class_map = {'ok': 'status-ok', 'problema': 'status-problema', 'manutencao': 'status-manutencao'}

        return JsonResponse({
            'success': True, 'message': 'Chamado atualizado!', 'chamado_id': chamado.id,
            'novo_status_chamado_display': chamado.get_status_chamado_display(),
            'computador_id': computador.id,
            'computador_status_reportado_display': computador.get_status_reportado_display(),
            'computador_status_reportado_class': status_class_map.get(computador.status_reportado, ''),
            'html_chamados_atualizado': render_to_string(
                'assets/partials/lista_chamados_para_modal.html',
                {'chamados': ChamadoManutencao.objects.filter(computador=computador).order_by('-data_abertura')}
            ),
            # ...
        'html_form_chamado_atualizado': render_to_string(
            'assets/partials/form_atualizar_chamado_para_modal.html',
            {'ultimo_chamado_valido_para_acao': proximo_chamado_para_acao,  # Passa o correto
             'computador': computador,
             'user': request.user,  # Passar o usuário para o template parcial do formulário
             'perms': request.user.get_all_permissions()}  # Passar permissões para o template parcial
        )
        })
    except ChamadoManutencao.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Chamado não encontrado.'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

    # assets/views.py
    # ... (imports existentes, incluindo login_required, permission_required, ChamadoManutencao) ...


@login_required
@permission_required('assets.change_chamadomanutencao', raise_exception=True)  # Usuário precisa poder alterar
def editar_chamado_view(request, chamado_id):
    chamado = get_object_or_404(ChamadoManutencao, id=chamado_id)

    if request.method == 'POST':
        form = ChamadoManutencaoUpdateForm(request.POST, instance=chamado)
        if form.is_valid():
            instancia_chamado = form.save(commit=False)
            # Se o status mudou para resolvido/fechado e não havia data de resolução, preenche
            if instancia_chamado.status_chamado in ['resolvido', 'fechado'] and not instancia_chamado.data_resolucao:
                instancia_chamado.data_resolucao = timezone.now()
            elif instancia_chamado.status_chamado not in ['resolvido', 'fechado']:
                instancia_chamado.data_resolucao = None  # Limpa se foi reaberto

            # Se o chamado não tem técnico e um foi selecionado no form
            if not chamado.tecnico_responsavel and instancia_chamado.tecnico_responsavel:
                pass  # O form já atribui
            # Se nenhum técnico foi selecionado e o chamado ainda não tem técnico,
            # e o usuário logado é um técnico/admin, atribui a ele mesmo.
            elif not instancia_chamado.tecnico_responsavel and not chamado.tecnico_responsavel and \
                    (request.user.is_staff or request.user.groups.filter(name__in=['Helpdesk', 'Admin']).exists()):
                instancia_chamado.tecnico_responsavel = request.user

            instancia_chamado.save()  # Isso também chamará o método save() do model ChamadoManutencao
            # que tem a lógica para atualizar o status do computador.

            messages.success(request, f'Chamado #{chamado.id} atualizado com sucesso!')
            return redirect('assets:lista_chamados')  # Redireciona para a lista de chamados
        else:
            messages.error(request, 'Por favor, corrija os erros abaixo.')
    else:  # GET request
        form = ChamadoManutencaoUpdateForm(instance=chamado)

    context = {
        'form': form,
        'chamado': chamado,
        'page_title': f'Editar Chamado #{chamado.id} - {chamado.titulo}'
    }
    return render(request, 'assets/editar_chamado.html', context)


# TODO: Adicionar view para ping (AJAX)


# ... (outras views) ...

@login_required
@permission_required('assets.view_computador', raise_exception=True)
@require_GET
def ping_computador_view(request, comp_id):
    # ... (corpo da função como antes, usando executar_ping) ...
    # COPIE O CORPO COMPLETO DESTA FUNÇÃO DA SUA VERSÃO FUNCIONAL ANTERIOR
    # Certifique-se de que ela retorna o JsonResponse como esperado
    computador = get_object_or_404(Computador, id=comp_id)
    ip_address_obj = computador.ip_associado
    status_text_map = {'online': 'Online', 'offline': 'Offline', 'unreachable': 'Inalcançável', 'timeout': 'Timeout',
                       'error_ping': 'Erro Ping', 'error_ping_cmd_not_found': 'Erro Cmd Ping', 'no_ip': 'Sem IP'}
    status_class_map = {'online': 'bg-success', 'offline': 'bg-danger', 'unreachable': 'bg-warning',
                        'timeout': 'bg-warning', 'error_ping': 'bg-dark', 'error_ping_cmd_not_found': 'bg-dark',
                        'no_ip': 'bg-secondary'}
    ip_to_ping = None
    online_status = 'no_ip'

    if ip_address_obj:
        ip_to_ping = ip_address_obj.address
        online_status = executar_ping(ip_to_ping)
        computador.status_rede = online_status
        computador.ultimo_ping_status = timezone.now()
        computador.save(update_fields=['status_rede', 'ultimo_ping_status'])

    return JsonResponse({
        'success': True, 'online_status': online_status,
        'status_text': status_text_map.get(online_status, 'Desconhecido'),
        'status_class': status_class_map.get(online_status, 'bg-light text-dark'),
        'computador_id': computador.id, 'ip_pingado': ip_to_ping
    })


@login_required
@permission_required('assets.change_computador', raise_exception=True) # Mudar posição é mudar o computador
@require_POST
def update_computador_position_view(request, comp_id):
    # ... (corpo da função como antes, pegando pos_x, pos_y do JSON) ...
    # COPIE O CORPO COMPLETO DESTA FUNÇÃO DA SUA VERSÃO FUNCIONAL ANTERIOR
    try:
        computador = get_object_or_404(Computador, id=comp_id)
        data = json.loads(request.body)
        new_pos_x = data.get('pos_x')
        new_pos_y = data.get('pos_y')
        if new_pos_x is not None and new_pos_y is not None:
            computador.pos_x = int(new_pos_x)
            computador.pos_y = int(new_pos_y)
            computador.save(update_fields=['pos_x', 'pos_y'])
            return JsonResponse({'success': True, 'message': 'Posição atualizada.'})
        else:
            return JsonResponse({'success': False, 'error': 'Dados de posição ausentes.'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Payload JSON inválido.'}, status=400)
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Valores de posição inválidos.'}, status=400)
    except Computador.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Computador não encontrado.'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Erro interno: {str(e)}'}, status=500)

@login_required
@permission_required('assets.view_computador', raise_exception=True)  # Apenas quem pode ver computadores
def lista_computadores_view(request):
    lista_de_computadores = Computador.objects.all().order_by('nome_host').select_related('ip_associado')

    # TODO: Adicionar filtros (por setor, etc.) e busca no futuro
    # TODO: Adicionar paginação se a lista for muito grande

    context = {
        'computadores': lista_de_computadores,
        'page_title': 'Gerenciamento de Computadores'
    }
    return render(request, 'assets/lista_computadores.html', context)

# TODO: Importar arquvivo CSV

@login_required
@permission_required('assets.add_computador', raise_exception=True)  # Usuário precisa poder adicionar computadores
def importar_computadores_view(request):
    form = CSVImportForm()
    import_results = None  # Para armazenar os resultados da importação

    if request.method == 'POST':
        form = CSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            delimiter = form.cleaned_data['delimiter']

            # Verificar extensão do arquivo (opcional, mas bom)
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'Formato de arquivo inválido. Por favor, envie um arquivo .csv')
            else:
                try:
                    # A função processar_csv_computadores espera um objeto de arquivo aberto em modo binário para o Pandas
                    # request.FILES['csv_file'] já é um objeto de arquivo adequado (UploadedFile)
                    import_results = processar_csv_computadores(csv_file, delimiter)

                    if import_results['errors_count'] == 0 and not import_results['errors_list']:
                        messages.success(request,
                                         f"Importação concluída! Criados: {import_results['created_count']}, Atualizados: {import_results['updated_count']}, Pulados: {import_results['skipped_count']}.")
                    else:
                        messages.warning(request,
                                         f"Importação com problemas. Criados: {import_results['created_count']}, Atualizados: {import_results['updated_count']}, Pulados: {import_results['skipped_count']}, Erros: {import_results['errors_count']}.")
                    # Mesmo com erros parciais, podemos querer mostrar os resultados.
                    # Se quiser redirecionar apenas em sucesso total:
                    # if import_results['errors_count'] == 0 and not import_results['errors_list'] and (import_results['created_count'] > 0 or import_results['updated_count'] > 0):
                    #    return redirect('assets:lista_computadores')

                except Exception as e:
                    messages.error(request, f"Ocorreu um erro inesperado durante a importação: {e}")
        else:
            messages.error(request, "Houve um erro com o formulário enviado.")

    context = {
        'form': form,
        'page_title': 'Importar Computadores de CSV',
        'import_results': import_results  # Passa os resultados para o template
    }
    return render(request, 'assets/importar_computadores_form.html', context)