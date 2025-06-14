# assets/utils.py
import subprocess
import platform

from django.utils import timezone
import pandas as pd
from django.db import transaction
from .models import Computador, IPAddress
# Não precisamos de models aqui diretamente, eles serão passados como argumento

def executar_ping(ip_address):
    """
    Executa um ping para o endereço IP fornecido e retorna o status.

    Retorna:
        str: 'online', 'offline', 'unreachable', 'timeout', 'error_ping', 'no_ip'
    """
    if not ip_address:
        return 'no_ip'

    try:
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        # Ajuste para timeout: Windows usa -w em milissegundos, Linux/Mac -W em segundos.
        # Usando 1 pacote, timeout de 500ms (0.5s).
        if platform.system().lower() == 'windows':
            command = ['ping', param, '1', '-w', '500', ip_address]
        else:
            # Para Linux/Mac, -W é o timeout em segundos. Algumas versões de ping usam -t para TTL, não timeout.
            # Vamos usar -W para timeout de espera pela resposta.
            command = ['ping', param, '1', '-W', '0.5', ip_address]


        startupinfo = None
        if platform.system().lower() == 'windows':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo)
        stdout, stderr = process.communicate(timeout=2) # Timeout geral para o processo Popen

        # Tenta decodificar a saída. cp{numero_da_pagina_de_codigo_do_console_windows} ou utf-8
        # É melhor tentar uma lista ou usar locale.getpreferredencoding()
        # Por simplicidade, tentaremos alguns comuns.
        try:
            output_str = stdout.decode('utf-8')
        except UnicodeDecodeError:
            try:
                output_str = stdout.decode('cp850') # Comum no console Windows PT-BR
            except UnicodeDecodeError:
                output_str = stdout.decode('latin-1', errors='ignore')


        if process.returncode == 0:
            # Algumas versões do ping no Windows retornam 0 mesmo para 'Host de destino inacessível'.
            # Precisamos verificar a saída do stdout.
            if platform.system().lower() == 'windows':
                if 'inacess¡vel' in output_str.lower() or 'unreachable' in output_str.lower() or 'tempo esgotado' in output_str.lower() or 'timed out' in output_str.lower():
                    if 'inacess¡vel' in output_str.lower() or 'unreachable' in output_str.lower():
                         return 'unreachable'
                    return 'timeout' # Se for "tempo esgotado"
            return 'online'
        elif 'Host de destino inacess¡vel' in output_str.lower() or \
             'Destination host unreachable' in output_str.lower():
            return 'unreachable'
        elif 'Esgotado o tempo limite do pedido' in output_str or \
             'Request timed out' in output_str.lower(): # Menos provável de chegar aqui se o returncode não for 0
            return 'timeout'
        else:
            return 'offline' # Genérico para outros erros de ping com returncode != 0

    except subprocess.TimeoutExpired:
        return 'timeout' # Timeout da função communicate
    except FileNotFoundError: # Se o comando ping não for encontrado
        print("Comando 'ping' não encontrado. Verifique se está no PATH do sistema.")
        return 'error_ping_cmd_not_found'
    except Exception as e:
        print(f"Erro inesperado ao executar ping para {ip_address}: {e}")
        return 'error_ping' # Erro genérico na execução do ping


@transaction.atomic  # Garante que ou tudo é importado, ou nada se ocorrer um erro
def processar_csv_computadores(csv_file_object, delimiter):
    """
    Processa um arquivo CSV carregado para importar computadores.
    Retorna um dicionário com estatísticas e erros.
    """
    results = {
        'created_count': 0,
        'updated_count': 0,
        'skipped_count': 0,
        'errors_count': 0,
        'errors_list': []  # Lista de mensagens de erro detalhadas
    }

    try:
        # Pandas pode ler diretamente de um objeto de arquivo em memória (UploadedFile)
        df = pd.read_csv(csv_file_object, sep=delimiter, encoding='utf-8', dtype=str).fillna('')
        df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]  # Normaliza cabeçalhos

        if 'nome_host' not in df.columns:
            results['errors_list'].append("Coluna 'nome_host' não encontrada no cabeçalho do CSV.")
            results['errors_count'] = len(df)  # Marca todas as linhas como erro se o cabeçalho estiver faltando
            return results

    except Exception as e:
        results['errors_list'].append(f"Erro ao ler ou parsear o arquivo CSV: {str(e)}")
        return results

    for index, row in df.iterrows():
        try:
            nome_host = row.get('nome_host', '').strip()
            if not nome_host:
                results['errors_list'].append(f"Linha {index + 2}: nome_host está vazio. Pulando.")
                results['skipped_count'] += 1
                continue

            descricao = row.get('descricao', '')
            setor = row.get('setor', '')
            ip_str = row.get('ip_associado', '').strip()  # Nome da coluna no CSV
            pos_x_str = row.get('pos_x', '0').strip()
            pos_y_str = row.get('pos_y', '0').strip()
            status_reportado_csv = row.get('status_reportado', 'ok').strip().lower()

            pos_x = int(pos_x_str) if pos_x_str else 0
            pos_y = int(pos_y_str) if pos_y_str else 0

            status_reportado = 'ok'  # Default
            if status_reportado_csv in dict(Computador.STATUS_CHOICES).keys():
                status_reportado = status_reportado_csv
            else:
                results['errors_list'].append(
                    f"Linha {index + 2} ({nome_host}): status_reportado '{status_reportado_csv}' inválido. Usando 'ok'.")

            ip_obj = None
            if ip_str:
                try:
                    ip_obj = IPAddress.objects.get(address=ip_str)
                except IPAddress.DoesNotExist:
                    # Opção: Criar IP se não existir?
                    # ip_obj, created_ip = IPAddress.objects.get_or_create(address=ip_str, defaults={'descricao': f"IP para {nome_host}"})
                    # if created_ip: results['messages'].append(f"IP {ip_str} criado para {nome_host}.")
                    results['errors_list'].append(
                        f"Linha {index + 2} ({nome_host}): IP '{ip_str}' não encontrado no banco. Computador será salvo sem IP ou a linha será pulada.")
                    # Decida se quer pular a linha ou salvar sem IP. Por enquanto, salva sem IP.

            computador, created = Computador.objects.update_or_create(
                nome_host=nome_host,
                defaults={
                    'descricao': descricao,
                    'setor': setor,
                    'ip_associado': ip_obj,
                    'pos_x': pos_x,
                    'pos_y': pos_y,
                    'status_reportado': status_reportado,
                }
            )

            if created:
                results['created_count'] += 1
            else:
                results['updated_count'] += 1

        except ValueError as ve:
            results['errors_list'].append(f"Linha {index + 2} ({row.get('nome_host', 'N/A')}): Erro de valor - {ve}.")
            results['errors_count'] += 1
        except Exception as e:
            results['errors_list'].append(f"Linha {index + 2} ({row.get('nome_host', 'N/A')}): Erro inesperado - {e}.")
            results['errors_count'] += 1

    return results