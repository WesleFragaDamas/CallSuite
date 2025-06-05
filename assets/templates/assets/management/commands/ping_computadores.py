# assets/management/commands/ping_computadores.py
import time
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from assets.models import Computador, IPAddress # Importe seus modelos
from assets.utils import executar_ping # Importe a função de ping

class Command(BaseCommand):
    help = 'Executa ping em todos os computadores com IP associado e atualiza seu status de rede.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--intervalo',
            type=int,
            default=1, # Segundos de intervalo entre pings para não sobrecarregar a rede/máquina
            help='Intervalo em segundos entre cada tentativa de ping.',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100, # Processa em lotes para não carregar todos os computadores na memória de uma vez
            help='Número de computadores a processar por lote.',
        )

    def handle(self, *args, **options):
        intervalo = options['intervalo']
        batch_size = options['batch_size']

        self.stdout.write(self.style.SUCCESS(f"Iniciando verificação de ping para computadores... Intervalo: {intervalo}s, Lote: {batch_size}"))

        # Contadores
        total_computadores_verificados = 0
        online_count = 0
        offline_count = 0
        no_ip_count = 0
        error_count = 0

        # Query para pegar computadores que têm um IP associado
        queryset = Computador.objects.filter(ip_associado__isnull=False).select_related('ip_associado')
        total_a_verificar = queryset.count()

        if total_a_verificar == 0:
            self.stdout.write(self.style.WARNING("Nenhum computador com IP associado encontrado para verificar."))
            return

        self.stdout.write(f"Total de computadores com IP para verificar: {total_a_verificar}")

        # Processamento em lotes
        for i in range(0, total_a_verificar, batch_size):
            batch_queryset = queryset[i:i + batch_size]
            self.stdout.write(f"Processando lote {i//batch_size + 1}...")

            for computador in batch_queryset:
                ip_para_pingar = computador.ip_associado.address
                self.stdout.write(f"  Verificando {computador.nome_host} ({ip_para_pingar})... ", ending="")

                status_rede_atual = executar_ping(ip_para_pingar)

                if status_rede_atual == 'online':
                    self.stdout.write(self.style.SUCCESS("Online"))
                    online_count += 1
                elif status_rede_atual == 'no_ip': # Não deveria acontecer devido ao filtro do queryset
                    self.stdout.write(self.style.WARNING("Sem IP (inesperado)"))
                    no_ip_count += 1
                elif status_rede_atual in ['error_ping', 'error_ping_cmd_not_found']:
                    self.stdout.write(self.style.ERROR(f"Erro ({status_rede_atual})"))
                    error_count += 1
                else: # offline, unreachable, timeout
                    self.stdout.write(self.style.WARNING(f"{status_rede_atual.capitalize()}"))
                    offline_count += 1

                # Atualiza o computador no banco
                computador.status_rede = status_rede_atual
                computador.ultimo_ping_status = timezone.now()
                computador.save(update_fields=['status_rede', 'ultimo_ping_status'])

                total_computadores_verificados += 1
                time.sleep(intervalo) # Pausa entre os pings

        self.stdout.write(self.style.SUCCESS("\n--- Resumo da Verificação de Ping ---"))
        self.stdout.write(f"Total de Computadores Verificados: {total_computadores_verificados}")
        self.stdout.write(self.style.SUCCESS(f"Online: {online_count}"))
        self.stdout.write(self.style.WARNING(f"Offline/Inalcançável/Timeout: {offline_count}"))
        if no_ip_count > 0:
            self.stdout.write(self.style.NOTICE(f"Sem IP (inesperado): {no_ip_count}"))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"Erros de Ping: {error_count}"))
        self.stdout.write(self.style.SUCCESS("Verificação de ping concluída."))