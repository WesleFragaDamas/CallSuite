# assets/management/commands/import_computadores_csv.py
import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from assets.models import Computador, IPAddress  # Seus modelos
from django.db import transaction  # Para atomicidade da transação


class Command(BaseCommand):
    help = 'Importa computadores de um arquivo CSV usando Pandas'

    def add_arguments(self, parser):
        parser.add_argument('csv_file_path', type=str, help='O caminho completo para o arquivo CSV.')
        parser.add_argument(
            '--delimiter',
            type=str,
            default=',',  # Padrão para vírgula, mas pode ser alterado
            help='O delimitador usado no arquivo CSV (padrão: vírgula). Use ";" para ponto e vírgula.'
        )

    @transaction.atomic  # Garante que ou tudo é importado, ou nada se ocorrer um erro
    def handle(self, *args, **options):
        file_path = options['csv_file_path']
        delimiter = options['delimiter']
        self.stdout.write(self.style.SUCCESS(
            f"Iniciando importação de computadores do arquivo: {file_path} usando delimitador '{delimiter}'"))

        try:
            df = pd.read_csv(file_path, sep=delimiter, encoding='utf-8', dtype=str).fillna('')
            # dtype=str para ler tudo como string inicialmente e evitar conversões automáticas do Pandas
            # .fillna('') para substituir NaN por strings vazias, o que pode ser mais fácil de tratar
        except FileNotFoundError:
            raise CommandError(f"Arquivo não encontrado: {file_path}")
        except Exception as e:
            raise CommandError(f"Erro ao ler o arquivo CSV com Pandas: {e}")

        created_count = 0
        updated_count = 0
        skipped_count = 0
        errors_count = 0

        for index, row in df.iterrows():
            try:
                nome_host = row.get('nome_host', '').strip()
                if not nome_host:
                    self.stderr.write(self.style.WARNING(f"Linha {index + 2}: nome_host está vazio. Pulando."))
                    skipped_count += 1
                    continue

                descricao = row.get('descricao', '')
                setor = row.get('setor', '')
                ip_str = row.get('ip_associado', '').strip()
                pos_x_str = row.get('pos_x', '0').strip()
                pos_y_str = row.get('pos_y', '0').strip()
                status_reportado = row.get('status_reportado', 'ok').strip().lower()  # Padrão 'ok'

                # Validação e conversão de tipos
                pos_x = int(pos_x_str) if pos_x_str else 0
                pos_y = int(pos_y_str) if pos_y_str else 0

                if status_reportado not in dict(Computador.STATUS_CHOICES).keys():
                    self.stderr.write(self.style.WARNING(
                        f"Linha {index + 2} ({nome_host}): status_reportado '{status_reportado}' inválido. Usando 'ok'."))
                    status_reportado = 'ok'

                ip_obj = None
                if ip_str:
                    try:
                        # Tenta encontrar. Se quiser criar IPs automaticamente: use get_or_create
                        ip_obj = IPAddress.objects.get(address=ip_str)
                    except IPAddress.DoesNotExist:
                        self.stderr.write(self.style.WARNING(
                            f"Linha {index + 2} ({nome_host}): IP '{ip_str}' não encontrado. Computador será salvo sem IP."))
                        # Se quiser criar o IP automaticamente:
                        # ip_obj, created = IPAddress.objects.get_or_create(address=ip_str, defaults={'descricao': f"IP para {nome_host}"})
                        # if created: self.stdout.write(self.style.SUCCESS(f"  IP {ip_str} criado."))

                computador, created = Computador.objects.update_or_create(
                    nome_host=nome_host,
                    defaults={
                        'descricao': descricao,
                        'setor': setor,
                        'ip_associado': ip_obj,
                        'pos_x': pos_x,
                        'pos_y': pos_y,
                        'status_reportado': status_reportado,
                        # status_rede é gerenciado pelo ping, não importamos
                    }
                )

                if created:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f"  Criado: {computador.nome_host}"))
                else:
                    updated_count += 1
                    self.stdout.write(f"  Atualizado: {computador.nome_host}")

            except ValueError as ve:
                self.stderr.write(self.style.ERROR(
                    f"Linha {index + 2} ({row.get('nome_host', 'N/A')}): Erro de valor - {ve}. Pulando."))
                errors_count += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(
                    f"Linha {index + 2} ({row.get('nome_host', 'N/A')}): Erro inesperado - {e}. Pulando."))
                errors_count += 1

        self.stdout.write(self.style.SUCCESS("\n--- Resumo da Importação ---"))
        self.stdout.write(self.style.SUCCESS(f"Criados: {created_count}"))
        self.stdout.write(f"Atualizados: {updated_count}")
        if skipped_count > 0: self.stdout.write(self.style.WARNING(f"Pulados (nome_host vazio): {skipped_count}"))
        if errors_count > 0: self.stdout.write(self.style.ERROR(f"Linhas com erro: {errors_count}"))
        self.stdout.write(self.style.SUCCESS("Importação de computadores concluída."))