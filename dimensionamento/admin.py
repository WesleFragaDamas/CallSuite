# dimensionamento/admin.py
from django.contrib import admin
from .models import CenarioDimensionamento, ComponenteShrinkage, VolumePorIntervalo, TurnoPlanejado, IntervaloProgramado

# Inlines para permitir adicionar/editar itens relacionados na mesma página do CenarioDimensionamento
class ComponenteShrinkageInline(admin.TabularInline):
    model = ComponenteShrinkage
    extra = 3  # Começa com 3 formulários vazios para adicionar componentes
    fields = ('nome_componente', 'percentual')
    verbose_name_plural = "Componentes de Shrinkage (Ex: Pausa, Treinamento, Absenteísmo)"


class VolumePorIntervaloInline(admin.TabularInline):
    model = VolumePorIntervalo
    extra = 0
    fields = ('get_intervalo_display', 'volume_chamadas')
    readonly_fields = ('get_intervalo_display',)
    ordering = ('intervalo_programado__hora_inicio',)
    verbose_name_plural = "Volumes de Chamadas por Intervalo"
    max_num = 48 # Garante que não mais que 48 podem ser adicionados

    def get_intervalo_display(self, obj):
        if obj.pk and obj.intervalo_programado:
            return obj.intervalo_programado.hora_inicio.strftime('%H:%M')
        return "Novo Intervalo"
    get_intervalo_display.short_description = "Intervalo"

class TurnoPlanejadoInline(admin.TabularInline):
    model = TurnoPlanejado
    extra = 1 # Mostrar um formulário em branco para adicionar um turno
    fields = ('hora_inicio_turno', 'hora_fim_turno', 'numero_agentes_neste_turno')
    verbose_name_plural = "Turnos Planejados de Agentes"


@admin.register(CenarioDimensionamento)
class CenarioDimensionamentoAdmin(admin.ModelAdmin):
    list_display = ('nome_cenario', 'tipo_dimensionamento', 'data_referencia', 'usuario_criador', 'data_modificacao',
                    'get_total_shrinkage_percent')
    list_filter = ('tipo_dimensionamento', 'data_referencia', 'usuario_criador')
    search_fields = ('nome_cenario', 'usuario_criador__username')
    readonly_fields = ('data_criacao', 'data_modificacao', 'usuario_criador')

    fieldsets = (
        (None, {'fields': ('nome_cenario', 'tipo_dimensionamento', 'data_referencia')}),
        ('Parâmetros Base (Receptivo)', {'description': "Parâmetros principais para cálculo de Erlang C.", 'fields': (
        'tma_segundos', 'nivel_servico_percentual_meta', 'nivel_servico_tempo_meta_segundos')}),
        ('Informações do Registro',
         {'fields': ('usuario_criador', 'data_criacao', 'data_modificacao'), 'classes': ('collapse',), }),
    )
    # ATUALIZE A LISTA DE INLINES:
    inlines = [ComponenteShrinkageInline, VolumePorIntervaloInline, TurnoPlanejadoInline]

    def save_model(self, request, obj, form, change):
        if not obj.pk: obj.usuario_criador = request.user
        super().save_model(request, obj, form, change)

    def get_total_shrinkage_percent(self, obj):
        soma_percentuais = sum(c.percentual for c in obj.componentes_shrinkage.all())
        return f"{soma_percentuais:.2f}%"

    get_total_shrinkage_percent.short_description = "Shrinkage Total (%)"

@admin.register(IntervaloProgramado)
class IntervaloProgramadoAdmin(admin.ModelAdmin):
    list_display = ('hora_inicio',)
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False