from django.db import models

class IPAddress(models.Model):
    address = models.GenericIPAddressField(unique=True, verbose_name="Endereço IP")
    descricao = models.CharField(max_length=255, blank=True, null=True, verbose_name="Descrição")
    # Outros campos relevantes para o IP: Gateway, DNS, VLAN, status (reservado, em uso, livre)
    # status_ip = models.CharField(max_length=20, choices=[('livre', 'Livre'), ('uso', 'Em Uso'), ('reservado', 'Reservado')], default='livre')
    # data_cadastro = models.DateTimeField(auto_now_add=True)
    # ultima_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.address

    class Meta:
        verbose_name = "Endereço IP"
        verbose_name_plural = "Endereços IP"

#-------------------------------------------------------------------------------------------------------------#
#                   Model Computador                                                                          #
#-------------------------------------------------------------------------------------------------------------#

from django.db import models
# from django.contrib.auth.models import User # Se quiser associar um usuário padrão à máquina

class Computador(models.Model):
    nome_host = models.CharField(max_length=100, unique=True, verbose_name="Nome do Host/Etiqueta")
    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição/Observações")
    setor = models.CharField(max_length=100, blank=True, null=True, verbose_name="Setor/Departamento")
    ip_associado = models.OneToOneField(
        IPAddress,
        on_delete=models.SET_NULL, # Se o IP for deletado, a máquina não é deletada, apenas fica sem IP
        blank=True,
        null=True,
        verbose_name="IP Associado"
    )
    # Campos para posicionamento no layout (vamos discutir como armazenar isso)
    pos_x = models.IntegerField(default=0, verbose_name="Posição X no Layout")
    pos_y = models.IntegerField(default=0, verbose_name="Posição Y no Layout")

    STATUS_CHOICES = [
        ('ok', 'OK'),
        ('problema', 'Com Problema'),
        ('manutencao', 'Em Manutenção'),
    ]
    status_reportado = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ok',
        verbose_name="Status Reportado"
    )
    STATUS_REDE_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('erro_ip', 'IP Incorreto'),  # Para a ideia de verificar se o IP da máquina é o esperado
        ('nao_verificado', 'Não Verificado'),
    ]
    status_rede = models.CharField(
        max_length=20,
        choices=STATUS_REDE_CHOICES,
        default='nao_verificado',
        verbose_name="Status da Rede (Ping)"
    )
    ultimo_ping_status = models.DateTimeField(
        blank=True, null=True, verbose_name="Última Verificação de Ping"
    )
    # usuario_principal = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name="computador_principal")
    # data_cadastro = models.DateTimeField(auto_now_add=True)
    # ultima_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nome_host

    class Meta:
        verbose_name = "Computador"
        verbose_name_plural = "Computadores"

#-------------------------------------------------------------------------------------------------------------
#                Model ChamadoManutencao
#-------------------------------------------------------------------------------------------------------------

from django.db import models
from django.contrib.auth.models import User # Para saber quem abriu e quem é o técnico

class ChamadoManutencao(models.Model):
    computador = models.ForeignKey('Computador', on_delete=models.CASCADE, verbose_name="Computador") # Use aspas se Computador vier depois
    titulo = models.CharField(max_length=200, verbose_name="Título do Problema")
    descricao_problema = models.TextField(verbose_name="Descrição Detalhada")
    data_abertura = models.DateTimeField(auto_now_add=True, verbose_name="Data de Abertura")
    aberto_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='chamados_abertos',
        verbose_name="Aberto Por"
    )
    tecnico_responsavel = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='chamados_atribuidos',
        verbose_name="Técnico Responsável"
    )
    STATUS_CHAMADO_CHOICES = [
        ('aberto', 'Aberto'),
        ('em_atendimento', 'Em Atendimento'),
        ('aguardando_peca', 'Aguardando Peça'),
        ('resolvido', 'Resolvido'),
        ('fechado', 'Fechado'), # Adicionei Fechado como um status final também
    ]
    status_chamado = models.CharField(
        max_length=20,
        choices=STATUS_CHAMADO_CHOICES,
        default='aberto',
        verbose_name="Status do Chamado"
    )
    data_resolucao = models.DateTimeField(blank=True, null=True, verbose_name="Data de Resolução")
    solucao_aplicada = models.TextField(blank=True, null=True, verbose_name="Solução Aplicada")

    # Para guardar o status anterior e detectar a mudança
    _original_status_chamado = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_status_chamado = self.status_chamado

    def save(self, *args, **kwargs):
        is_new = self._state.adding # Verifica se é um novo objeto sendo criado
        super().save(*args, **kwargs) # Salva o chamado primeiro

        # Lógica para atualizar o status do computador associado
        if not is_new and self.status_chamado != self._original_status_chamado:
            if self.status_chamado in ['resolvido', 'fechado']:
                # Verifica se há outros chamados NÃO resolvidos/fechados para o mesmo computador
                outros_chamados_abertos = ChamadoManutencao.objects.filter(
                    computador=self.computador
                ).exclude(
                    status_chamado__in=['resolvido', 'fechado']
                ).exclude(
                    pk=self.pk # Exclui o próprio chamado atual da contagem
                ).exists()

                if not outros_chamados_abertos:
                    # Se não houver outros chamados abertos, marca o computador como OK
                    self.computador.status_reportado = 'ok'
                    # Poderíamos também resetar o status_rede para 'nao_verificado' ou 'online' se desejado
                    # self.computador.status_rede = 'online' # Ou 'nao_verificado'
                    self.computador.save()
                # Se houver outros chamados abertos, o status do computador permanece 'problema'
                # ou o que quer que seja, não mudamos aqui.
            elif self._original_status_chamado in ['resolvido', 'fechado'] and self.status_chamado not in ['resolvido', 'fechado']:
                # Se um chamado foi reaberto (estava resolvido/fechado e agora não está mais)
                if self.computador.status_reportado == 'ok':
                    self.computador.status_reportado = 'problema' # Ou um status apropriado para reaberto
                    self.computador.save()


        self._original_status_chamado = self.status_chamado # Atualiza o status original para a próxima vez

    def __str__(self):
        return f"Chamado #{self.id} - {self.computador.nome_host} - {self.titulo}"

    class Meta:
        verbose_name = "Chamado de Manutenção"
        verbose_name_plural = "Chamados de Manutenção"
        ordering = ['-data_abertura']