import requests
import json
from src.gera_excel import cria_excel, converter_json_para_excel
from time import sleep
import numpy as np
from src.gera_excel_pedidos import exportar_para_excel
import pandas as pd


def convert_numpy(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    return obj


def get_user_id(ACCESS_TOKEN):
    # URL para obter informações do usuário logado
    API_URL = "https://api.mercadolibre.com/users/me"

    # Headers com autenticação
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    # Fazer requisição para obter o User ID
    response = requests.get(API_URL, headers=headers)

    # Verificar se a requisição foi bem-sucedida
    if response.status_code == 200:
        user_data = response.json()
        user_id = user_data.get("id")
        print(f"Seu User ID no Mercado Livre é: {user_id}")
        return user_id
    else:
        print(f"Erro ao obter User ID: {response.text}")


def consulta_produtos(USER_ID, ACCESS_TOKEN):
    # URL para obter produtos ativos (à venda)
    API_URL = f"https://api.mercadolibre.com/users/{USER_ID}/items/search?status=active&limit=20&offset=0"


    # Headers com autenticação
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    # Fazer requisição para obter os produtos
    response = requests.get(API_URL, headers=headers)

    # Verificar se a requisição foi bem-sucedida
    if response.status_code == 200:
        data = response.json()
        item_ids = data.get("results", [])

        print(f"Produtos encontrados: {len(item_ids)}")

        # Caso tenha produtos, buscar detalhes dos produtos
        if item_ids:
            item_details_url = f"https://api.mercadolibre.com/items?ids={','.join(item_ids)}"
            details_response = requests.get(item_details_url, headers=headers)

            if details_response.status_code == 200:
                items = details_response.json()
                print(json.dumps(items, indent=2, ensure_ascii=False))
            else:
                print(f"Erro ao obter detalhes dos produtos: {details_response.text}")
        else:
            print("Nenhum produto encontrado.")

    else:
        print(f"Erro ao buscar produtos: {response.text}")


def generate_report(ACCESS_TOKEN):
    url = "https://api.mercadolibre.com/billing/integration/periods/key/2025-02-01/reports"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "group": "ML",
        "document_type": "BILL",
        "report_format": "XLSX"
    }

    response = requests.post(url, json=data, headers=headers)

    return response.json()


def get_report_status(ACCESS_TOKEN, report_id):
    url = f"https://api.mercadolibre.com/billing/integration/reports/{report_id}/status?document_type=BILL"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers)

    return response.json()


def get_order_by_id(ACCESS_TOKEN, order_id):

    API_URL = f"https://api.mercadolibre.com/orders/{order_id}"

    # Headers com autenticação
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    # Fazer requisição para obter os produtos
    response = requests.get(API_URL, headers=headers)

    return response.json()


def get_order_by_period(ACCESS_TOKEN, period_key):

    API_URL = f"https://api.mercadolibre.com/billing/integration/periods/key/{period_key}/group/ML/details?document_type=BILL&limit=1000&from_id=0"

    # Headers com autenticação
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    # Fazer requisição para obter os produtos
    response = requests.get(API_URL, headers=headers)

    return response.json()


def get_billing_info(ACCESS_TOKEN, shipping_id):

    # API_URL = f"https://api.mercadolibre.com/shipments/{shipping_id}/costs"
    # API_URL = f"https://api.mercadolibre.com/shipments/{shipping_id}/payments"
    # API_URL = f"https://api.mercadolibre.com/shipments/{shipping_id}/billing_info"
    API_URL = f"https://api.mercadolibre.com/shipments/{shipping_id}/invoice_data?siteId=MLB"


    # Headers com autenticação
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    # Fazer requisição para obter os produtos
    response = requests.get(API_URL, headers=headers)

    return response.json()


def get_billing_cost_info(ACCESS_TOKEN, shipping_id):

    API_URL = f"https://api.mercadolibre.com/shipments/{shipping_id}/costs"
    # API_URL = f"https://api.mercadolibre.com/shipments/{shipping_id}/payments"
    # API_URL = f"https://api.mercadolibre.com/shipments/{shipping_id}/billing_info"
    # API_URL = f"https://api.mercadolibre.com/shipments/{shipping_id}/invoice_data?siteId=MLB"


    # Headers com autenticação
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    # Fazer requisição para obter os produtos
    response = requests.get(API_URL, headers=headers)

    return response.json()


def get_periodos(ACCESS_TOKEN):

    API_URL = f"https://api.mercadolibre.com/billing/integration/monthly/periods?group=ML&document_type=BILL&offset=1&limit=4"

    # Headers com autenticação
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    # Fazer requisição para obter os produtos
    response = requests.get(API_URL, headers=headers)

    return response.json()



def consulta_teste(ACCESS_TOKEN):
    # URL para obter produtos ativos (à venda)

    API_URL = f"https://api.mercadolibre.com/orders/search?seller=276359269"
    API_URL = "https://api.mercadolibre.com/billing/integration/periods/key/2025-03-01/group/ML/details?document_type=BILL&limit=1000&from_id=0"


    # Headers com autenticação
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    # Fazer requisição para obter os produtos
    response = requests.get(API_URL, headers=headers)

    return response.json()


def consulta_pedido_por_pedido(ACCESS_TOKEN, df_pedidos):
    all_orders = []  # Lista para armazenar os JSONs retornados
    all_relatorio = []
    relatorio = {}
    # for index, row in df_pedidos.iloc[:20].iterrows():
    for index, row in df_pedidos.iterrows():
        relatorio = {}
        order_id = row['sales_info_order_id']
        relatorio["order_id"] = order_id
        print(f"Índice: {index}, A: {order_id}")
        response_order = get_order_by_id(ACCESS_TOKEN, order_id)
        order_status = response_order['status']

        # print(response)
        shipping_id = response_order['shipping']['id']
        relatorio["shipping_id"] = shipping_id
        shipping_response = get_billing_info(ACCESS_TOKEN, shipping_id)
        # print(shipping_response)
        invoice_number = shipping_response.get('invoice_number', '')
        invoice_amount = shipping_response.get('invoice_amount', '')
        response_order['invoice_number'] = invoice_number
        response_order['invoice_amount'] = invoice_amount
        relatorio["invoice_number"] = invoice_number
        relatorio["invoice_amount"] = invoice_amount
        shipping_cost_response = get_billing_cost_info(ACCESS_TOKEN, shipping_id)
        # print("Shipping cost response: ")
        # print(shipping_cost_response)
        frete_cliente = shipping_cost_response.get('receiver', {}).get("cost", 0)
        frete_empresa = sum(item.get("cost", 0) for item in shipping_cost_response.get('senders', []))

        marketplace_fee = sum(item.get("marketplace_fee", 0) for item in response_order.get('payments', []))

        response_order['frete_cliente'] = frete_cliente
        response_order['frete_empresa'] = frete_empresa
        response_order['marketplace_fee'] = marketplace_fee
        relatorio["frete_cliente"] = frete_cliente
        relatorio["frete_empresa"] = frete_empresa
        relatorio["marketplace_fee"] = marketplace_fee
        relatorio["order_status"] = order_status
        relatorio["buyer_nickname"] = response_order.get("buyer", {}).get("nickname", "")
        first_name = response_order.get("buyer", {}).get("first_name", "")
        last_name = response_order.get("buyer", {}).get("last_name", "")
        relatorio["buyer_fullname"] = first_name + " " + last_name

        all_orders.append(response_order)  # Adiciona o JSON à lista
        all_relatorio.append(relatorio)

        print(f'pedido consultado na API: {order_id}')
        sleep(0.2)

    # Salvar o resultado em um arquivo JSON
    with open("../dados/pedidos.json", "w", encoding="utf-8") as f:
        json.dump(all_orders, f, ensure_ascii=False, indent=4, default=convert_numpy)

    # Salvar o resultado em um arquivo JSON
    with open("../dados/dados_relatorio.json", "w", encoding="utf-8") as f:
        json.dump(all_relatorio, f, ensure_ascii=False, indent=4, default=convert_numpy)

    print("Arquivo 'pedidos.json' salvo com sucesso!")


def cria_relatorio(ACCESS_TOKEN):
    period_key = '2025-01-01'
    response = get_order_by_period(ACCESS_TOKEN, period_key)
    # print(response)

    df_pedidos = cria_excel(response)  # retorna lista de orders

    # Consulta pedido por pedido e salva todos no arquivo pedidos.json
    consulta_pedido_por_pedido(ACCESS_TOKEN, df_pedidos)


if __name__ == "__main__":
    # Configurações (substitua pelos seus valores)
    ACCESS_TOKEN = 'APP_USR-612439810072537-032013-4b79dad395bdbc0d83b020e52e90e7c9-276359269'
    # USER_ID = get_user_id(ACCESS_TOKEN)  # Você pode obter esse ID com /users/me
    # print(USER_ID)

    # PASSO 1 - criar relatório gerando dados
    # cria_relatorio(ACCESS_TOKEN)


    arquivo_json = "../dados/dados_relatorio.json"  # Substitua pelo caminho do seu arquivo JSON
    arquivo_excel = "../dados/Vendas_Online.xlsx"  # Nome do arquivo Excel de saída
    converter_json_para_excel(arquivo_json, arquivo_excel)

    # order_id = '2000010277939390'
    # response = get_order_by_id(ACCESS_TOKEN, order_id)
    # print(response)


    # Consulta Numero NF e Código de acesso
    # shipping_id = '44248868189'
    # shipping_response = get_billing_info(ACCESS_TOKEN, shipping_id)
    # print(shipping_response)
    # print("fim")


    # report = generate_report(ACCESS_TOKEN)
    # report_id = report['file_id']
    # print(report_id)

    # report_id = 'ML-M-report-BILL-2025-02-01-276359269-v4'
    # status_response = get_report_status(ACCESS_TOKEN, report_id)
    # status = status_response['status']
    # print(status)
    #
    # response = consulta_teste(ACCESS_TOKEN)
    # data = response.json()
    # vendas = data.get("results", [])
    # for venda in vendas:
    #     print(venda['status'])

    # response = get_periodos(ACCESS_TOKEN)
    # print(response)


    # order_id = '2000010268238790'
    # response = get_order_by_id(ACCESS_TOKEN, order_id)
    # print(response)

    # shiping_id = '44378242321'
    # response = get_billing_info(ACCESS_TOKEN, shiping_id)
    # print(response)

    # response = consulta_teste(ACCESS_TOKEN)
    # print(response['results'])

    # USER_ID = '11635294'
    # consulta_produtos(USER_ID, ACCESS_TOKEN)