import requests
import json
from dotenv import load_dotenv
from utils.ml_autenticacao import atualizar_token_com_refresh_token
from utils.gera_excel import converter_json_para_excel
from utils.tratamento_de_dados import cria_dataframe_com_dados_dos_pedidos, consilida_dados_dos_pedidos
from utils.api_mercado_livre import consulta_pedido_por_pedido, get_periodos, get_user_id, get_order_by_period, consulta_dados_cliente, get_billing_info
from utils.api_mercadolivre_testes import get_nf_by_order_id, get_all_shipmentts_info
from utils.acesso_webmais import consulta_numero_nf_por_doc_cliente
import os
from datetime import datetime, timezone
from time import sleep

load_dotenv()

def consulta_teste(ACCESS_TOKEN, period_key):


    API_URL = f'https://api.mercadolibre.com/billing/integration/periods/key/{period_key}/summary/details?document_type=BILL'

    # Headers com autenticação
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    try:
        response = requests.get(API_URL, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except (requests.exceptions.RequestException, requests.exceptions.ConnectTimeout) as e:
        print(f"Erro na Consuta da API: {API_URL}")
        print(f"Aguardando 2 segundos para nova tentativa.")
        sleep(2)  # Aguarda 2 segundos antes de tentar novamente


def main():

    expiration_str = os.getenv("ML_ACCESSTOKEN_EXPIRATION")
    if not expiration_str:
        atualizar_token_com_refresh_token()
        print("Token ML atualizado!!")
    else:
        expiration_dt = datetime.fromisoformat(expiration_str)
        if expiration_dt.tzinfo is None:
            expiration_dt = expiration_dt.replace(tzinfo=timezone.utc)

        if datetime.now(timezone.utc) > expiration_dt:
            atualizar_token_com_refresh_token()
            print("Token ML atualizado!!")

    ACCESS_TOKEN = os.getenv("ML_ACCESSTOKEN")


    period_key = '2026-03-01'
    retorno_json = consulta_teste(ACCESS_TOKEN, period_key)
    print("retornado")

    input("digite algo para sair")

if __name__ == "__main__":
    main()