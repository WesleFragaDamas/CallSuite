# dimensionamento/utils.py
import math
import datetime  # Import datetime no nível do módulo


# Não importar models do app aqui para evitar importação circular se este utils
# for importado por models.py em algum momento. Passaremos instâncias de model
# ou usaremos imports locais dentro das funções quando estritamente necessário.

def factorial(n_float):
    n = int(n_float)  # Garante que é um inteiro para math.factorial
    if n < 0:
        raise ValueError("Factorial não definido para números negativos")
    if n == 0:
        return 1
    return math.factorial(n)


def erlang_c_formula(A_traffic_intensity, N_agents_float):
    """Calcula a probabilidade de uma chamada ter que esperar (Erlang C - Pw)."""
    N_agents = int(N_agents_float)  # Agentes devem ser inteiros

    if N_agents <= 0: return 1.0
    if A_traffic_intensity <= 0: return 0.0

    # A fórmula clássica de Erlang C requer N > A para estabilidade.
    # Se N <= A, a fila teoricamente cresce indefinidamente.
    # Para fins de cálculo de Pw, se N <= A, a probabilidade de espera é muito alta.
    if N_agents <= A_traffic_intensity:
        # Se N_agents == A_traffic_intensity, a fórmula original tem (N-A) no denominador, causando divisão por zero.
        # Vamos retornar um valor muito alto para Pw, indicando que quase todas as chamadas esperam.
        return 0.99999

    try:
        # Termo A^N / N!
        term_A_N_div_N_fact = (A_traffic_intensity ** N_agents) / factorial(N_agents)

        # Somatório de (A^k / k!) para k de 0 a N-1
        sum_val = 0
        for k_loop in range(N_agents):  # k_loop de 0 a N_agents-1
            sum_val += (A_traffic_intensity ** k_loop) / factorial(k_loop)

        # Probabilidade de espera (Pw)
        numerator_pw = term_A_N_div_N_fact * (N_agents / (N_agents - A_traffic_intensity))
        denominator_pw = sum_val + numerator_pw

        if denominator_pw == 0:  # Evitar divisão por zero se algo muito estranho acontecer
            return 1.0

        Pw = numerator_pw / denominator_pw
        return max(0.0, min(Pw, 1.0))  # Garante que Pw está entre 0 e 1

    except (OverflowError, ValueError) as e:
        print(f"Erro no cálculo de Erlang C (A={A_traffic_intensity}, N={N_agents}): {e}")
        return 0.99999  # Indica alta probabilidade de espera ou erro


def calculate_service_level(A_traffic_intensity, N_agents_float, tma_seconds, target_time_seconds):
    """Calcula o Nível de Serviço (probabilidade de uma chamada ser atendida DENTRO do target_time)."""
    N_agents = int(N_agents_float)

    if N_agents <= 0 or tma_seconds <= 0: return 0.0
    if A_traffic_intensity <= 0: return 1.0  # Sem tráfego, 100% SLA

    # Se N_agents <= A_traffic_intensity, o SLA será muito baixo ou zero.
    # A função erlang_c_formula já lida com N_agents == A_traffic_intensity.
    # Se N_agents < A_traffic_intensity, a ocupação > 100%, SLA = 0.
    if N_agents < A_traffic_intensity:
        return 0.00001  # Quase zero

    Pw = erlang_c_formula(A_traffic_intensity, N_agents)

    # SL = 1 - Pw * e^(-(N-A) * (target_time / TMA))
    try:
        # (N-A) pode ser zero se N=A, o que faria math.exp(0)=1. Pw seria alto.
        # Se N > A, (N-A) > 0.
        exponent_factor = (N_agents - A_traffic_intensity) * (target_time_seconds / tma_seconds)
        service_level = 1.0 - (Pw * math.exp(-exponent_factor))
    except OverflowError:
        service_level = 0.0

    return max(0.0, min(service_level, 1.0))  # Garante que SL esteja entre 0 e 1


def find_agents_for_sla(volume_per_hour, tma_seconds, target_sla_percent, target_sla_seconds, max_agents_to_check=200,
                        start_n_factor=1.05):
    """Encontra o número mínimo de agentes (N) para atingir um SLA específico."""
    if volume_per_hour <= 0 or tma_seconds <= 0: return 0

    A = (volume_per_hour * tma_seconds) / 3600.0
    if A <= 0: return 0

    # Começa a testar com N > A. Um bom ponto de partida pode ser A + sqrt(A) ou A * 1.1
    # Ou simplesmente o primeiro inteiro maior que A.
    # N_start = math.floor(A) + 1
    N_start = math.ceil(A * start_n_factor)  # Começa um pouco acima de A
    if N_start <= A:  # Garante que N_start seja estritamente maior que A
        N_start = math.floor(A) + 1
    if N_start == 0 and A > 0:  # Se A é muito pequeno mas > 0, precisa de pelo menos 1 agente
        N_start = 1

    for n_test in range(int(N_start), int(N_start) + max_agents_to_check):
        if n_test == 0: continue  # Não faz sentido testar com 0 agentes se há tráfego
        current_sl = calculate_service_level(A, n_test, tma_seconds, target_sla_seconds)
        if current_sl >= target_sla_percent:
            return n_test

    # Se não atingiu, retorna um indicador de que o número de agentes é alto ou inatingível com os params
    print(
        f"AVISO: SLA de {target_sla_percent * 100}% não alcançado com {int(N_start) + max_agents_to_check - 1} agentes para A={A:.2f}. Retornando valor limite.")
    return int(N_start) + max_agents_to_check


def calcular_dimensionamento_receptivo(cenario):  # cenario é uma instância de CenarioDimensionamento
    from .models import IntervaloProgramado  # Import local para evitar importação circular

    resultados_por_intervalo = []
    intervalos_programados_objs = list(IntervaloProgramado.objects.all().order_by('hora_inicio'))
    if not intervalos_programados_objs or len(intervalos_programados_objs) != 48:
        raise ValueError("Os 48 Intervalos Programados fixos não estão cadastrados corretamente no banco.")

    volumes_map = {vol.intervalo_programado_id: vol.volume_chamadas for vol in cenario.volumes_intervalo.all()}
    turnos_do_cenario = list(cenario.turnos_planejados.all())

    fator_shrinkage = cenario.get_fator_shrinkage_aplicado()
    tma_cenario_seg = cenario.tma_segundos
    meta_sla_perc_target = cenario.nivel_servico_percentual_meta
    meta_sla_tempo_seg_target = cenario.nivel_servico_tempo_meta_segundos

    for ip_obj in intervalos_programados_objs:
        intervalo_atual_inicio_time = ip_obj.hora_inicio  # datetime.time

        volume_neste_intervalo = volumes_map.get(ip_obj.pk, 0)
        volume_hora_equivalente = volume_neste_intervalo * 2  # Converte volume de 30min para 1h

        agentes_brutos_erlang = 0
        if volume_hora_equivalente > 0 and tma_cenario_seg > 0:
            agentes_brutos_erlang = find_agents_for_sla(
                volume_hora_equivalente,
                tma_cenario_seg,
                meta_sla_perc_target,
                meta_sla_tempo_seg_target
            )

        agentes_recomendados_com_shrinkage = 0
        if agentes_brutos_erlang > 0 and fator_shrinkage != float('inf'):
            agentes_recomendados_com_shrinkage = math.ceil(agentes_brutos_erlang * fator_shrinkage)

        agentes_acumulados_neste_intervalo = 0
        intervalo_atual_inicio_time = ip_obj.hora_inicio
        for turno in turnos_do_cenario:
            if turno.hora_inicio_turno <= intervalo_atual_inicio_time and intervalo_atual_inicio_time < turno.hora_fim_turno:
                agentes_acumulados_neste_intervalo += turno.numero_agentes_neste_turno
            # Adicionar lógica para turnos que cruzam meia-noite se ainda não estiver perfeita
            elif turno.hora_inicio_turno > turno.hora_fim_turno:  # Turno cruza meia-noite
                if intervalo_atual_inicio_time >= turno.hora_inicio_turno or intervalo_atual_inicio_time < turno.hora_fim_turno:
                    agentes_acumulados_neste_intervalo += turno.numero_agentes_neste_turno

        # SLA e Ocupação são calculados com base nos agentes_acumulados (oferta real dos turnos)
        sla_previsto_base = 0.0
        ocupacao_prevista_base = 0.0
        if agentes_acumulados_neste_intervalo > 0 and volume_hora_equivalente > 0 and tma_cenario_seg > 0:
            # ... (cálculo de intensidade_trafego_A) ...
            # ... (chamada a calculate_service_level e cálculo de ocupação usando agentes_acumulados_neste_intervalo) ...
            intensidade_trafego_A = (volume_hora_equivalente * tma_cenario_seg) / 3600.0
            if intensidade_trafego_A > 0:
                sla_previsto_base = calculate_service_level(
                    intensidade_trafego_A, agentes_acumulados_neste_intervalo, tma_cenario_seg,
                    meta_sla_tempo_seg_target
                ) * 100
                ocupacao_prevista_base = (
                                                     intensidade_trafego_A / agentes_acumulados_neste_intervalo) * 100 if agentes_acumulados_neste_intervalo > 0 else float(
                    'inf')
                ocupacao_prevista_base = min(100.0, ocupacao_prevista_base)

        resultados_por_intervalo.append({
            'intervalo_pk_str': str(ip_obj.pk),
            'intervalo_str': intervalo_atual_inicio_time.strftime('%H:%M'),
            'volume_chamadas': volume_neste_intervalo,
            'agentes_brutos_erlang': int(round(agentes_brutos_erlang)),
            'agentes_recomendados_com_shrinkage': int(round(agentes_recomendados_com_shrinkage)),
            'agentes_acumulados_oferta_turnos': agentes_acumulados_neste_intervalo,  # Calculado dos turnos
            'agentes_para_simulacao_inicial': agentes_acumulados_neste_intervalo,
            # Para o valor inicial do input editável
            'sla_previsto_base': sla_previsto_base,  # SLA com base na oferta dos turnos
            'ocupacao_prevista_base': ocupacao_prevista_base,  # Ocupação com base na oferta dos turnos
        })
    return resultados_por_intervalo