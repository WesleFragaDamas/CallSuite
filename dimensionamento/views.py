# dimensionamento/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
import datetime
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET  # Adicionado require_GET se não estava
from django.template.loader import render_to_string

from .models import (
    CenarioDimensionamento,
    ComponenteShrinkage,
    VolumePorIntervalo,
    TurnoPlanejado,  # Adicionado
    IntervaloProgramado
)
from .forms import (
    CenarioDimensionamentoForm,
    ComponenteShrinkageFormSet,
    VolumePorIntervaloFormSet,
    TurnoPlanejadoFormSet  # Adicionado, e HorarioAgenteDefinidoFormSet removido dos imports se estava
)
from .utils import calcular_dimensionamento_receptivo, \
    calculate_service_level  # Supondo que calculate_service_level também está em utils


@login_required
@permission_required('dimensionamento.add_cenariodimensionamento', raise_exception=True)
@permission_required('dimensionamento.change_cenariodimensionamento', raise_exception=True)
def criar_editar_cenario_view(request, cenario_id=None):
    if cenario_id:
        cenario_instance = get_object_or_404(CenarioDimensionamento, id=cenario_id)
        page_title = f"Editar Cenário: {cenario_instance.nome_cenario}"
    else:
        cenario_instance = None
        page_title = "Criar Novo Cenário de Dimensionamento"

    intervalos_programados_objs = list(IntervaloProgramado.objects.all().order_by('hora_inicio'))
    if len(intervalos_programados_objs) != 48:
        messages.error(request,
                       "Configuração crítica: Os 48 Intervalos Programados não estão cadastrados. Contate o administrador.")
        return redirect('dashboard')  # Ou uma página de erro apropriada

    if request.method == 'POST':
        form = CenarioDimensionamentoForm(request.POST, instance=cenario_instance)
        shrinkage_formset = ComponenteShrinkageFormSet(request.POST, instance=cenario_instance, prefix='shrinkages')
        volume_formset = VolumePorIntervaloFormSet(request.POST, instance=cenario_instance, prefix='volumes')
        turno_formset = TurnoPlanejadoFormSet(request.POST, instance=cenario_instance, prefix='turnos')  # Novo formset

        if form.is_valid() and shrinkage_formset.is_valid() and volume_formset.is_valid() and turno_formset.is_valid():
            try:
                with transaction.atomic():
                    cenario_salvo = form.save(commit=False)
                    if not cenario_salvo.pk:
                        cenario_salvo.usuario_criador = request.user
                    cenario_salvo.save()  # Salva CenarioDimensionamento

                    # Salva formsets
                    shrinkage_formset.instance = cenario_salvo
                    shrinkage_formset.save()

                    volume_formset.instance = cenario_salvo
                    volume_formset.save()

                    turno_formset.instance = cenario_salvo  # Salva o novo formset de turnos
                    turno_formset.save()

                messages.success(request, f"Cenário '{cenario_salvo.nome_cenario}' salvo com sucesso!")
                return redirect('dimensionamento:resultados_cenario', cenario_id=cenario_salvo.id)
            except Exception as e:
                messages.error(request, f"Ocorreu um erro ao salvar o cenário: {str(e)}")
                print(f"Erro ao salvar cenário: {e}")  # Log para o console do servidor
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
            if not form.is_valid(): print(f"CenarioForm Erros: {form.errors.as_json()}")
            if not shrinkage_formset.is_valid(): print(
                f"ShrinkageFormSet Erros: {shrinkage_formset.errors} {shrinkage_formset.non_form_errors()}")
            if not volume_formset.is_valid(): print(
                f"VolumeFormSet Erros: {volume_formset.errors} {volume_formset.non_form_errors()}")
            if not turno_formset.is_valid(): print(
                f"TurnoFormSet Erros: {turno_formset.errors} {turno_formset.non_form_errors()}")


    else:  # GET request
        form = CenarioDimensionamentoForm(instance=cenario_instance)
        shrinkage_formset = ComponenteShrinkageFormSet(instance=cenario_instance, prefix='shrinkages')
        turno_formset = TurnoPlanejadoFormSet(instance=cenario_instance, prefix='turnos')  # Para os turnos

        # Prepara dados iniciais para o VolumePorIntervaloFormSet (48 forms)
        initial_volumes_data = []
        existing_volumes_map = {}
        if cenario_instance:  # Se estiver editando
            existing_volumes_map = {vol.intervalo_programado_id: vol for vol in
                                    cenario_instance.volumes_intervalo.all()}
        for ip_obj in intervalos_programados_objs:  # intervalos_programados_objs são os 48 IntervaloProgramado
            vol_instance = existing_volumes_map.get(ip_obj.pk)
            initial_volumes_data.append({
                'intervalo_programado': ip_obj,  # Passa o OBJETO IntervaloProgramado
                'volume_chamadas': vol_instance.volume_chamadas if vol_instance else 0
                # Se vol_instance existir, o formset deve usar os dados da instância para este form.
                # Se não existir, usa este 'initial'.

            })

        # Ao instanciar com 'instance' E 'initial', o Django é um pouco peculiar.
        # 'initial' é usado para forms extras (além dos ligados à instância).
        # Como definimos min_num=48, max_num=48 no FormSet, ele deve criar 48 forms.
        # Para forms que correspondem a instâncias existentes, 'instance' prevalece.
        # Para forms "novos" (para completar os 48), 'initial' é usado.
        volume_formset = VolumePorIntervaloFormSet(
            prefix='volumes',
            instance=cenario_instance,  # Carrega os VolumePorIntervalo existentes para este cenário
            initial=initial_volumes_data  # Fornece dados para forms que não correspondem a uma instância salva
            # E crucialmente, o objeto intervalo_programado para todos
        )

    context = {
        'form': form, 'shrinkage_formset': shrinkage_formset, 'volume_formset': volume_formset,
        'turno_formset': turno_formset, 'page_title': page_title, 'cenario': cenario_instance,
        # 'todos_intervalos_programados': intervalos_programados_objs # Não estritamente necessário se o initial do formset tem a info
    }

    return render(request, 'dimensionamento/cenario_form.html', context)


@login_required
# A permissão aqui pode ser 'view_cenariodimensionamento' se é apenas para simulação
@permission_required('dimensionamento.view_cenariodimensionamento', raise_exception=True)
@require_POST
def atualizar_agentes_alocados_ajax(request):  # Renomeei para refletir que não salva no HorarioAgenteDefinido
    try:
        cenario_id = request.POST.get('cenario_id')
        intervalo_pk_str = request.POST.get('intervalo_pk_str')
        agentes_simulados_str = request.POST.get('agentes_alocados')  # Vem do input com esse nome

        if not all([cenario_id, intervalo_pk_str, agentes_simulados_str]):
            return JsonResponse({'success': False, 'error': 'Dados incompletos.'}, status=400)

        agentes_simulados = int(agentes_simulados_str)
        if agentes_simulados < 0:
            return JsonResponse({'success': False, 'error': 'Agentes simulados não pode ser negativo.'}, status=400)

        cenario = get_object_or_404(CenarioDimensionamento, id=cenario_id)
        intervalo_obj = get_object_or_404(IntervaloProgramado, pk=intervalo_pk_str)

        # NÃO SALVA NADA NO BANCO PARA ESTA VERSÃO DE SIMULAÇÃO PURA
        # Apenas recalcula com base nos agentes_simulados

        volume_obj = VolumePorIntervalo.objects.filter(cenario=cenario, intervalo_programado=intervalo_obj).first()
        volume_intervalo = volume_obj.volume_chamadas if volume_obj else 0
        volume_hora_para_erlang = volume_intervalo * 2

        sla_previsto = 0.0
        ocupacao_prevista = 0.0

        if agentes_simulados > 0 and volume_hora_para_erlang > 0 and cenario.tma_segundos > 0:
            intensidade_A = (volume_hora_para_erlang * cenario.tma_segundos) / 3600.0
            if intensidade_A > 0:
                sla_previsto = calculate_service_level(
                    intensidade_A, agentes_simulados,
                    cenario.tma_segundos, cenario.nivel_servico_tempo_meta_segundos
                ) * 100
                ocupacao_prevista = (intensidade_A / agentes_simulados) * 100 if agentes_simulados > 0 else float('inf')
                ocupacao_prevista = min(100.0, ocupacao_prevista)

        return JsonResponse({
            'success': True,
            'message': 'Cálculo de simulação refeito.',  # Mensagem diferente
            'intervalo_pk_str': intervalo_pk_str,
            'novo_sla_previsto': round(sla_previsto, 2),
            'nova_ocupacao_prevista': round(ocupacao_prevista, 2)
        })
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Valor inválido para número de agentes.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# A view atualizar_agentes_alocados_ajax FOI REMOVIDA, pois a edição da alocação
# agora é feita através dos TurnoPlanejado na tela criar_editar_cenario_view.
# Se precisarmos de interatividade na tela de resultados no futuro para "simular"
# diferentes alocações, precisaremos de uma nova abordagem AJAX.

# Adicione suas outras views (lista_chamados_view, etc.) aqui, se estiverem neste arquivo.
# Se a view lista_cenarios_view ainda não foi criada, adicione-a.
@login_required
@permission_required('dimensionamento.view_cenariodimensionamento', raise_exception=True)
def listar_cenarios_view(request):
    from django.core.paginator import Paginator  # Import local
    cenarios_list = CenarioDimensionamento.objects.all().order_by('-data_modificacao')
    paginator = Paginator(cenarios_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {'page_obj': page_obj, 'page_title': 'Cenários de Dimensionamento'}
    return render(request, 'dimensionamento/listar_cenarios.html', context)

@login_required
@permission_required('dimensionamento.view_cenariodimensionamento', raise_exception=True)
def resultados_cenario_view(request, cenario_id): # <<< SEM '#' NO INÍCIO E NOME CORRETO
    cenario = get_object_or_404(CenarioDimensionamento, pk=cenario_id)
    resultados_calculados = []
    erro_calculo = None

    if cenario.tipo_dimensionamento == 'RECEPTIVO':
        try:
            resultados_calculados = calcular_dimensionamento_receptivo(cenario)
        except Exception as e:
            erro_calculo = f"Erro ao calcular dimensionamento: {str(e)}"
            messages.error(request, erro_calculo)
            print(f"Erro em calcular_dimensionamento_receptivo: {e}")
    else:
        erro_calculo = f"Cálculo para o tipo '{cenario.get_tipo_dimensionamento_display()}' ainda não implementado."
        messages.warning(request, erro_calculo)

    nivel_servico_meta_js = cenario.nivel_servico_percentual_meta * 100
    fator_shrinkage_obj = cenario.get_fator_shrinkage_aplicado()
    display_fator_shrinkage_extra_percent = 0.0
    if fator_shrinkage_obj != float('inf') and fator_shrinkage_obj > 1:
        display_fator_shrinkage_extra_percent = (fator_shrinkage_obj - 1) * 100

    context = {
        'cenario': cenario,
        'resultados': resultados_calculados,
        'page_title': f"Resultados: {cenario.nome_cenario}",
        'erro_calculo': erro_calculo,
        'nivel_servico_percentual_meta_para_js': nivel_servico_meta_js,
        'display_fator_shrinkage_calculado': fator_shrinkage_obj if fator_shrinkage_obj != float('inf') else "N/A",
        'display_fator_shrinkage_extra_percent': display_fator_shrinkage_extra_percent,
    }
    return render(request, 'dimensionamento/resultados_cenario.html', context)