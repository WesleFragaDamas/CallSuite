# assets/utils.py
import subprocess
import platform
from django.utils import timezone
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