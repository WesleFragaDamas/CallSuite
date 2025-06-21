# dimensionamento/management/commands/populate_intervalos.py
from django.core.management.base import BaseCommand
from dimensionamento.models import IntervaloProgramado
import datetime


class Command(BaseCommand):
    help = 'Popula a tabela IntervaloProgramado com os 48 intervalos de 30 minutos, se estiver vazia.'

    def handle(self, *args, **options):
        if IntervaloProgramado.objects.exists():
            self.stdout.write(
                self.style.WARNING('A tabela IntervaloProgramado já contém dados. Nenhuma ação foi tomada.'))
            return

        intervalos_a_criar = []
        start_time = datetime.time(0, 0)
        self.stdout.write('Criando os 48 intervalos de 30 minutos...')
        for i in range(48):
            current_interval_start = (datetime.datetime.combine(datetime.date.min, start_time) + datetime.timedelta(
                minutes=30 * i)).time()
            intervalos_a_criar.append(IntervaloProgramado(hora_inicio=current_interval_start))

        try:
            IntervaloProgramado.objects.bulk_create(intervalos_a_criar)
            self.stdout.write(
                self.style.SUCCESS(f'{len(intervalos_a_criar)} Intervalos Programados foram criados com sucesso.'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Erro ao criar intervalos: {e}'))