# assets/forms.py
from django import forms
from django.contrib.auth.models import User, Group # Import User e Group
from .models import ChamadoManutencao

class ChamadoManutencaoUpdateForm(forms.ModelForm): # Nome mais específico para o formulário de atualização
    class Meta:
        model = ChamadoManutencao
        fields = ['status_chamado', 'tecnico_responsavel', 'solucao_aplicada']
        widgets = {
            'solucao_aplicada': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
            'status_chamado': forms.Select(attrs={'class': 'form-select'}),
            'tecnico_responsavel': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = { # Personalizando labels (opcional, mas bom para clareza)
            'status_chamado': "Alterar Status para",
            'tecnico_responsavel': "Técnico Responsável",
            'solucao_aplicada': "Solução Aplicada / Notas Adicionais",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar o queryset do campo tecnico_responsavel
        # para mostrar apenas usuários que pertencem a grupos relevantes
        try:
            # Certifique-se que os nomes dos grupos correspondem exatamente aos que você criou no Admin
            grupos_tecnicos = Group.objects.filter(name__in=['Helpdesk', 'Admin', 'Supervisor'])
            if grupos_tecnicos.exists():
                self.fields['tecnico_responsavel'].queryset = User.objects.filter(
                    groups__in=grupos_tecnicos,
                    is_active=True # Apenas usuários ativos
                ).distinct().order_by('username')
            else:
                # Fallback se os grupos não forem encontrados (improvável se você os criou)
                self.fields['tecnico_responsavel'].queryset = User.objects.filter(is_staff=True, is_active=True).order_by('username')
        except Exception as e: # Captura genérica para o caso de Group.DoesNotExist ou outros problemas
            print(f"Erro ao filtrar técnicos no formulário: {e}")
            # Fallback mais seguro: não filtrar, ou mostrar apenas superusuários, ou deixar vazio
            self.fields['tecnico_responsavel'].queryset = User.objects.none() # Queryset vazio se houver erro

        # Tornar o campo tecnico_responsavel não obrigatório se já houver um técnico ou se o status for 'aberto'
        # e não queremos forçar a atribuição imediatamente.
        self.fields['tecnico_responsavel'].required = False

class CSVImportForm(forms.Form):
    csv_file = forms.FileField(label="Selecione o arquivo CSV")
    delimiter = forms.ChoiceField(
        label="Delimitador",
        choices=[
            (',', 'Vírgula (,)'),
            (';', 'Ponto e vírgula (;)'),
            ('\t', 'Tabulação (Tab)'),
        ],
        initial=',', # Padrão para vírgula
        widget=forms.Select(attrs={'class': 'form-select form-select-sm w-auto d-inline-block'})
    )