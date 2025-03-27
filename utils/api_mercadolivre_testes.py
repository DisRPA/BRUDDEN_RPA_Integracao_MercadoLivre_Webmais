import requests
from utils.ml_autenticacao import atualizar_token_com_refresh_token
import os
import json
from datetime import datetime, UTC


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


def get_nf_by_order_id(ACCESS_TOKEN, order_id, user_id='276359269'):
    API_URL = f"https://api.mercadolibre.com/users/{user_id}/invoices/orders/{order_id}"
    API_URL = f'https://api.mercadolibre.com/orders/{order_id}/billing_info'


    # Headers com autenticação
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    # Fazer requisição para obter os produtos
    response = requests.get(API_URL, headers=headers)

    return response.json()


def get_all_shipmentts_info(ACCESS_TOKEN, shipping_id):

    urls = {f"https://api.mercadolibre.com/shipments/{shipping_id}/costs",
            f"https://api.mercadolibre.com/shipments/{shipping_id}/payments",
            f"https://api.mercadolibre.com/shipments/{shipping_id}/billing_info",
            f"https://api.mercadolibre.com/shipments/{shipping_id}/delays",
            f"https://api.mercadolibre.com/shipments/{shipping_id}/history",
            f"https://api.mercadolibre.com/shipments/{shipping_id}/carrier",
            f"https://api.mercadolibre.com/shipments/{shipping_id}/invoice_data?siteId=MLB"
            }

    retorno = []

    for API_URL in urls:

        # Headers com autenticação
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}"
        }

        # Fazer requisição para obter os produtos
        response = requests.get(API_URL, headers=headers)

        json_response = response.json()

        retorno.append(json_response)

    return retorno



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



if __name__ == "__main__":
    expiration_str = os.getenv("ML_ACCESSTOKEN_EXPIRATION")
    if not expiration_str:
        atualizar_token_com_refresh_token()
        print("Token ML atualizado!!")
    else:
        expiration_dt = datetime.fromisoformat(expiration_str)
        if expiration_dt.tzinfo is None:
            expiration_dt = expiration_dt.replace(tzinfo=UTC)

        if datetime.now(UTC) > expiration_dt:
            atualizar_token_com_refresh_token()
            print("Token ML atualizado!!")

    ACCESS_TOKEN = os.getenv("ML_ACCESSTOKEN")


