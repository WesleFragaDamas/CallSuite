# dimensionamento/forms.py
from django import forms
from django.forms.models import inlineformset_factory
from .models import CenarioDimensionamento, ComponenteShrinkage, VolumePorIntervalo, TurnoPlanejado, IntervaloProgramado # Adicionado TurnoPlanejado

class CenarioDimensionamentoForm(forms.ModelForm):
    class Meta:
        model = CenarioDimensionamento
        fields = ['nome_cenario', 'tipo_dimensionamento', 'data_referencia',
                  'tma_segundos', 'nivel_servico_percentual_meta', 'nivel_servico_tempo_meta_segundos']
        widgets = {
            'nome_cenario': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'tipo_dimensionamento': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'data_referencia': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'tma_segundos': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'nivel_servico_percentual_meta': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
            'nivel_servico_tempo_meta_segundos': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
        }

ComponenteShrinkageFormSet = inlineformset_factory(
    CenarioDimensionamento, ComponenteShrinkage,
    fields=('nome_componente', 'percentual'), extra=1, can_delete=True,
    widgets={
        'nome_componente': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
        'percentual': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
    }
)

VolumePorIntervaloFormSet = inlineformset_factory(
    CenarioDimensionamento, VolumePorIntervalo,
    fields=('intervalo_programado', 'volume_chamadas'),
    extra=0, min_num=48, max_num=48, validate_min=True, can_delete=False,
    widgets={
        'intervalo_programado': forms.HiddenInput(),
        'volume_chamadas': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
    }
)

# --- NOVO FORMSET PARA TurnoPlanejado ---
TurnoPlanejadoFormSet = inlineformset_factory(
    CenarioDimensionamento,
    TurnoPlanejado,
    fields=('hora_inicio_turno', 'hora_fim_turno', 'numero_agentes_neste_turno'),
    extra=7, # Começa com um formulário de turno em branco
    can_delete=True,
    widgets={
        'hora_inicio_turno': forms.TimeInput(attrs={'class': 'form-control form-control-sm', 'type': 'time', 'step': '1800'}), # step 30 min
        'hora_fim_turno': forms.TimeInput(attrs={'class': 'form-control form-control-sm', 'type': 'time', 'step': '1800'}),
        'numero_agentes_neste_turno': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '1'}),
    }
)

# REMOVA HorarioAgenteDefinidoFormSet se ainda existir