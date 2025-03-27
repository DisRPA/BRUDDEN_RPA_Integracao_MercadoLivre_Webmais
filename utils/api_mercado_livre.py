import requests
import pandas as np
import json
from time import sleep
from utils.logger import logging


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
        logging.error(f"Erro ao obter User ID: {response.text}")


def get_periodos(ACCESS_TOKEN, quantidade=3):

    API_URL = f"https://api.mercadolibre.com/billing/integration/monthly/periods?group=ML&document_type=BILL&offset=1&limit={quantidade}"

    # Headers com autenticação
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    # Fazer requisição para obter os periodos
    response = (requests.get(API_URL, headers=headers)).json()
    for tentativa in range(3):
        try:
            response = requests.get(API_URL, headers=headers, timeout=10)
            response.raise_for_status()
            response = response.json()
            break
        except (requests.exceptions.RequestException, requests.exceptions.ConnectTimeout) as e:
            if tentativa < 2:
                logging.error(f"Erro na Consuta da API: {API_URL}")
                logging.info(f"Aguardando 2 segundos para nova tentativa.")
                sleep(2)  # Aguarda 2 segundos antes de tentar novamente
            else:
                raise e

    period_keys = []
    for result in response['results']:
        if result['period_status'] == 'CLOSED':
            period_keys.append(result['key'])

    return period_keys


def get_order_by_id(ACCESS_TOKEN, order_id):

    API_URL = f"https://api.mercadolibre.com/orders/{order_id}"

    # Headers com autenticação
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    # Fazer requisição para obter orders
    for tentativa in range(3):
        try:
            response = requests.get(API_URL, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, requests.exceptions.ConnectTimeout) as e:
            if tentativa < 2:
                logging.error(f"Erro na Consuta da API: {API_URL}")
                logging.info(f"Aguardando 2 segundos para nova tentativa.")
                sleep(2)  # Aguarda 2 segundos antes de tentar novamente
            else:
                raise e


def get_billing_cost_info(ACCESS_TOKEN, shipping_id):

    API_URL = f"https://api.mercadolibre.com/shipments/{shipping_id}/costs"
    # API_URL = f"https://api.mercadolibre.com/shipments/{shipping_id}/payments"
    # API_URL = f"https://api.mercadolibre.com/shipments/{shipping_id}/billing_info"
    # API_URL = f"https://api.mercadolibre.com/shipments/{shipping_id}/invoice_data?siteId=MLB"


    # Headers com autenticação
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    # Fazer requisição para obter os billing cost
    for tentativa in range(3):
        try:
            response = requests.get(API_URL, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, requests.exceptions.ConnectTimeout) as e:
            if tentativa < 2:
                logging.error(f"Erro na Consuta da API: {API_URL}")
                logging.info(f"Aguardando 2 segundos para nova tentativa.")
                sleep(2)  # Aguarda 2 segundos antes de tentar novamente
            else:
                raise e


def get_billing_info(ACCESS_TOKEN, shipping_id):

    # API_URL = f"https://api.mercadolibre.com/shipments/{shipping_id}/costs"
    # API_URL = f"https://api.mercadolibre.com/shipments/{shipping_id}/payments"
    # API_URL = f"https://api.mercadolibre.com/shipments/{shipping_id}/billing_info"
    API_URL = f"https://api.mercadolibre.com/shipments/{shipping_id}/invoice_data?siteId=MLB"


    # Headers com autenticação
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    # Fazer requisição para obter os billing info
    for tentativa in range(3):
        try:
            response = requests.get(API_URL, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, requests.exceptions.ConnectTimeout) as e:
            if tentativa < 2:
                logging.error(f"Erro na Consuta da API: {API_URL}")
                logging.info(f"Aguardando 2 segundos para nova tentativa.")
                sleep(2)  # Aguarda 2 segundos antes de tentar novamente
            else:
                raise e


def consulta_dados_cliente(ACCESS_TOKEN, order_id):
    API_URL = f'https://api.mercadolibre.com/orders/{order_id}/billing_info'

    # Headers com autenticação
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    # Fazer requisição para obter os produtos
    for tentativa in range(3):
        try:
            response = requests.get(API_URL, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, requests.exceptions.ConnectTimeout) as e:
            if tentativa < 2:
                logging.error(f"Erro na Consuta da API: {API_URL}")
                logging.info(f"Aguardando 2 segundos para nova tentativa.")
                sleep(2)  # Aguarda 2 segundos antes de tentar novamente
            else:
                raise e


def consulta_pedido_por_pedido(ACCESS_TOKEN, df_pedidos, period_key):
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
        shipping_id = response_order['shipping'].get('id', '')
        if not shipping_id:
            retorno_cliente = consulta_dados_cliente(ACCESS_TOKEN, order_id)
            response_order['cliente_doc_type'] = retorno_cliente['billing_info'].get('doc_type', '')
            relatorio['cliente_doc_type'] = retorno_cliente['billing_info'].get('doc_type', '')
            response_order['cliente_doc_number'] = retorno_cliente['billing_info'].get('doc_number', '')
            relatorio['cliente_doc_number'] = retorno_cliente['billing_info'].get('doc_number', '')


        relatorio["shipping_id"] = shipping_id
        shipping_response = get_billing_info(ACCESS_TOKEN, shipping_id)
        # print(shipping_response)
        total_amount = response_order['total_amount']
        paid_amount = response_order['paid_amount']
        pack_id = response_order.get('pack_id', '')
        relatorio["total_amount"] = total_amount
        relatorio["paid_amount"] = paid_amount
        relatorio["pack_id"] = pack_id

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
    with open(f"../dados/pedidos_{period_key}.json", "w", encoding="utf-8") as f:
        json.dump(all_orders, f, ensure_ascii=False, indent=4, default=convert_numpy)

    # Salvar o resultado em um arquivo JSON
    with open(f"../dados/dados_relatorio_{period_key}.json", "w", encoding="utf-8") as f:
        json.dump(all_relatorio, f, ensure_ascii=False, indent=4, default=convert_numpy)

    print("Arquivo 'pedidos.json' salvo com sucesso!")


def get_order_by_period(ACCESS_TOKEN, period_key):

    API_URL = f"https://api.mercadolibre.com/billing/integration/periods/key/{period_key}/group/ML/details?document_type=BILL&limit=1000&from_id=0"

    # Headers com autenticação
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    # Fazer requisição para obter orders por periodo
    for tentativa in range(3):
        try:
            response = requests.get(API_URL, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, requests.exceptions.ConnectTimeout) as e:
            if tentativa < 2:
                logging.error(f"Erro na Consuta da API: {API_URL}")
                logging.info(f"Aguardando 2 segundos para nova tentativa.")
                sleep(2)  # Aguarda 2 segundos antes de tentar novamente
            else:
                raise e


def consulta_dados_emissao_nf(ACCESS_TOKEN, order_id):


    API_URL = f'https://api.mercadolibre.com/orders/{order_id}/billing_info'

    # Headers com autenticação
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    # Fazer requisição para obter dados de emissão da nota
    for tentativa in range(3):
        try:
            response = requests.get(API_URL, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, requests.exceptions.ConnectTimeout) as e:
            if tentativa < 2:
                logging.error(f"Erro na Consuta da API: {API_URL}")
                logging.info(f"Aguardando 2 segundos para nova tentativa.")
                sleep(2)  # Aguarda 2 segundos antes de tentar novamente
            else:
                raise e