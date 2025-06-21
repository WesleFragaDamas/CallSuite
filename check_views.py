import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'callsuite.settings')
django.setup()

try:
    from dimensionamento import views

    print("Módulo dimensionamento.views importado com sucesso.")

    if hasattr(views, 'resultados_cenario_view'):
        print("Atributo 'resultados_cenario_view' ENCONTRADO em dimensionamento.views.")
        print(type(views.resultados_cenario_view))
    else:
        print("ERRO: Atributo 'resultados_cenario_view' NÃO ENCONTRADO em dimensionamento.views.")
        print("\nAtributos disponíveis em dimensionamento.views:")
        for attr_name in dir(views):
            if not attr_name.startswith('_'):  # Filtra atributos internos
                print(f"  - {attr_name}")

except ImportError as e:
    print(f"Erro de importação ao tentar importar dimensionamento.views: {e}")
except Exception as e_gen:
    print(f"Outro erro ao tentar importar ou verificar dimensionamento.views: {e_gen}")