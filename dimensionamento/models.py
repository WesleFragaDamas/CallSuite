# dimensionamento/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import datetime

class IntervaloProgramado(models.Model):
    hora_inicio = models.TimeField(unique=True, primary_key=True, verbose_name="Hora de Início do Intervalo")
    def __str__(self): return self.hora_inicio.strftime('%H:%M')
    class Meta: ordering = ['hora_inicio']; verbose_name = "Intervalo Programado (30 min)"; verbose_name_plural = "Intervalos Programados (30 min)"

class CenarioDimensionamento(models.Model):
    TIPO_DIMENSIONAMENTO_CHOICES = [('RECEPTIVO', 'Receptivo'), ('ATIVO', 'Ativo'), ('CHAT', 'Chat')]
    nome_cenario = models.CharField(max_length=150, verbose_name="Nome do Cenário")
    tipo_dimensionamento = models.CharField(max_length=15, choices=TIPO_DIMENSIONAMENTO_CHOICES, default='RECEPTIVO', verbose_name="Tipo")
    data_referencia = models.DateField(default=timezone.now, verbose_name="Data de Referência")
    tma_segundos = models.PositiveIntegerField(default=180, verbose_name="TMA (s)", help_text="Tempo Médio de Atendimento.")
    nivel_servico_percentual_meta = models.FloatField(default=0.80, validators=[MinValueValidator(0.01), MaxValueValidator(1.0)], verbose_name="NS Meta (%)", help_text="Ex: 0.80 para 80%")
    nivel_servico_tempo_meta_segundos = models.PositiveIntegerField(default=20, verbose_name="NS Tempo Meta (s)", help_text="Ex: 20 para atender em até 20s.")
    usuario_criador = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="cenarios_dimensionamento")
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_modificacao = models.DateTimeField(auto_now=True)
    def get_fator_shrinkage_aplicado(self):
        soma_percentuais = sum(c.percentual for c in self.componentes_shrinkage.all()) / 100.0
        if soma_percentuais >= 1: return float('inf')
        return 1 / (1 - soma_percentuais) if (1 - soma_percentuais) > 0 else float('inf')
    def get_total_shrinkage_percent_display(self):
        soma_percentuais = sum(c.percentual for c in self.componentes_shrinkage.all())
        return f"{soma_percentuais:.2f}%"
    def __str__(self): return f"{self.nome_cenario} ({self.get_tipo_dimensionamento_display()})"
    class Meta: verbose_name = "Cenário de Dimensionamento"; verbose_name_plural = "Cenários"; ordering = ['-data_modificacao']

class ComponenteShrinkage(models.Model):
    cenario = models.ForeignKey(CenarioDimensionamento, related_name='componentes_shrinkage', on_delete=models.CASCADE)
    nome_componente = models.CharField(max_length=100, verbose_name="Nome do Componente")
    percentual = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(100.0)], verbose_name="Percentual (%)", help_text="Ex: 10 para 10%.")
    def __str__(self): return f"{self.nome_componente}: {self.percentual}%"
    class Meta: verbose_name = "Componente de Shrinkage"; verbose_name_plural = "Componentes de Shrinkage"; unique_together = ('cenario', 'nome_componente')

class VolumePorIntervalo(models.Model):
    cenario = models.ForeignKey(CenarioDimensionamento, related_name='volumes_intervalo', on_delete=models.CASCADE)
    intervalo_programado = models.ForeignKey(IntervaloProgramado, on_delete=models.CASCADE, verbose_name="Intervalo")
    volume_chamadas = models.PositiveIntegerField(default=0, verbose_name="Volume Estimado")
    def __str__(self): return f"{self.intervalo_programado} - Vol: {self.volume_chamadas}"
    class Meta: verbose_name = "Volume por Intervalo"; verbose_name_plural = "Volumes por Intervalo"; ordering = ['intervalo_programado__hora_inicio']; unique_together = ('cenario', 'intervalo_programado')

class TurnoPlanejado(models.Model): # <<< NOSSO NOVO MODEL PARA TURNOS
    cenario = models.ForeignKey(CenarioDimensionamento, related_name='turnos_planejados', on_delete=models.CASCADE)
    hora_inicio_turno = models.TimeField(verbose_name="Início do Turno")
    hora_fim_turno = models.TimeField(verbose_name="Fim do Turno") # Ex: Se termina às 12:20, o último intervalo que cobre é 12:00. Às 12:30 não está mais.
    numero_agentes_neste_turno = models.PositiveIntegerField(default=1, verbose_name="Nº de Agentes Neste Turno")
    # Opcional: dias_semana = models.CharField(max_length=70, blank=True, help_text="Ex: Seg,Ter,Qua ou Seg-Sex")
    def __str__(self):
        return f"Turno {self.hora_inicio_turno.strftime('%H:%M')}-{self.hora_fim_turno.strftime('%H:%M')} ({self.numero_agentes_neste_turno} ag.) para {self.cenario.nome_cenario}"
    class Meta:
        verbose_name = "Turno Planejado"
        verbose_name_plural = "Turnos Planejados"
        ordering = ['cenario', 'hora_inicio_turno']