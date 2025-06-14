# assets/resources.py
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget # Para campos ForeignKey
from .models import Computador, IPAddress # Importe seus modelos

class ComputadorResource(resources.ModelResource):
    # Se você quiser importar/exportar o IP pelo seu endereço, e não pelo ID do IPAddress
    # Isso é útil se o seu CSV tiver o endereço IP em uma coluna.
    ip_associado_endereco = fields.Field(
        column_name='ip_associado', # Nome da coluna no seu CSV (pode ser 'ip' ou 'ip_address')
        attribute='ip_associado',
        widget=ForeignKeyWidget(IPAddress, field='address')
    )
    # Se o seu CSV tiver o ID do IPAddress, você não precisa do campo customizado acima para ip_associado.
    # O ModelResource já lidaria com ForeignKeys por ID por padrão.

    class Meta:
        model = Computador
        # Define os campos que serão incluídos na importação/exportação e sua ordem.
        # Se fields não for definido, todos os campos do model são incluídos.
        fields = ('id', 'nome_host', 'descricao', 'setor', 'ip_associado_endereco', 'pos_x', 'pos_y', 'status_reportado', 'status_rede')
        # Ou, se você quer que 'ip_associado' seja tratado pelo ID do IPAddress no CSV:
        # fields = ('id', 'nome_host', 'descricao', 'setor', 'ip_associado', 'pos_x', 'pos_y', 'status_reportado', 'status_rede')

        skip_unchanged = True # Não atualiza registros se os dados não mudaram
        report_skipped = True # Mostra quais registros foram pulados
        import_id_fields = ['nome_host'] # Usa 'nome_host' para identificar se um registro já existe e deve ser atualizado
                                       # Se não encontrar, cria um novo. Se 'id' for usado, ele tentará atualizar por ID.
                                       # Se você quiser que o 'id' do CSV seja usado para atualizar, use ['id'].
                                       # Se nome_host não for único, isso pode causar problemas. Use um campo único.
        # exclude = ('algum_campo_que_nao_quero_importar',)

    # Opcional: Limpar o valor do IP se vier vazio no CSV, para não dar erro no ForeignKeyWidget
    # def before_import_row(self, row, **kwargs):
    #     if 'ip_associado' in row and not row['ip_associado']: # Se a coluna ip_associado está vazia
    #         row['ip_associado'] = None # Define como None para o widget