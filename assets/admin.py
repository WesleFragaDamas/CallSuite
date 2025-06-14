from django.contrib import admin
from .models import IPAddress, Computador, ChamadoManutencao

from import_export.admin import ImportExportModelAdmin # Importe a classe base
from .resources import ComputadorResource # Importe seu resource


@admin.register(IPAddress)
class IPAddressAdmin(admin.ModelAdmin):
    list_display = ('address', 'descricao')
    search_fields = ('address', 'descricao')

@admin.register(Computador)
class ComputadorAdmin(ImportExportModelAdmin): # Mude de admin.ModelAdmin para ImportExportModelAdmin
    resource_class = ComputadorResource # Associe o resource
    list_display = ('nome_host', 'setor', 'ip_associado', 'status_reportado', 'status_rede', 'pos_x', 'pos_y')
    list_filter = ('setor', 'status_reportado', 'status_rede')
    search_fields = ('nome_host', 'descricao', 'ip_associado__address')
    autocomplete_fields = ['ip_associado']
    fieldsets = (
        (None, {'fields': ('nome_host', 'descricao', 'setor', 'ip_associado')}),
        ('Status e Posição', {'fields': ('status_reportado', 'pos_x', 'pos_y')}),
        # status_rede é preenchido pelo ping, não deve ser editável aqui geralmente
    )
    readonly_fields = ('status_rede', 'ultimo_ping_status') # Tornar campos de ping apenas leitura

@admin.register(ChamadoManutencao)
class ChamadoManutencaoAdmin(admin.ModelAdmin):
    list_display = ('id', 'computador', 'titulo', 'status_chamado', 'data_abertura', 'aberto_por', 'tecnico_responsavel')
    list_filter = ('status_chamado', 'data_abertura', 'tecnico_responsavel')
    search_fields = ('titulo', 'descricao_problema', 'computador__nome_host')
    raw_id_fields = ('computador', 'aberto_por', 'tecnico_responsavel')


# Para o autocomplete_fields no ComputadorAdmin funcionar, precisamos definir search_fields no IPAddressAdmin
# (já fizemos) e garantir que o model IPAddress tenha um método __str__ (já tem).