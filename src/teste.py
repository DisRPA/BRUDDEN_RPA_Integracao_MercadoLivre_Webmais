import json

def main():

    period_key = '2025-10-01'
    arquivo_json = f"../dados/dados_relatorio_{period_key}.json"  # Substitua pelo caminho do seu arquivo JSON
    # arquivo_json = f"../dados/dados_relatorio_consolidado_{period_key}.json"  # Substitua pelo caminho do seu arquivo JSON
    # arquivo_json = f"../dados/pedidos.json"
    # arquivo_excel = f"../dados/Vendas_Online_{period_key}.xlsx"  # Nome do arquivo Excel de saída

    with open(arquivo_json, 'r', encoding='utf-8') as f:
        dados = json.load(f)

    for dado in dados:
        print(dado['marketplace_fee'])
        # order_items = dado["order_items"]
        # for item in order_items:
        #     print(item['sale_fee'])


if __name__ == "__main__":
    main()