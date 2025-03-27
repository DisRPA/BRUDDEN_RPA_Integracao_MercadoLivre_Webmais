import requests
import json
from dotenv import load_dotenv
from utils.ml_autenticacao import atualizar_token_com_refresh_token
from utils.gera_excel import converter_json_para_excel
from utils.tratamento_de_dados import cria_dataframe_com_dados_dos_pedidos
from utils.api_mercado_livre import consulta_pedido_por_pedido, get_periodos, get_user_id, get_order_by_period
from utils.api_mercadolivre_testes import get_nf_by_order_id, get_all_shipmentts_info
import os
from datetime import datetime, UTC


load_dotenv()


def cria_relatorio(ACCESS_TOKEN, period_key):

    response = get_order_by_period(ACCESS_TOKEN, period_key)
    # print(response)

    df_pedidos = cria_df_com_dados_dos_pedidos(response)  # retorna lista de orders

    # Consulta pedido por pedido e salva todos no arquivo pedidos.json
    consulta_pedido_por_pedido(ACCESS_TOKEN, df_pedidos, period_key)


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


    # USER_ID = get_user_id(ACCESS_TOKEN)  # Você pode obter esse ID com /users/me
    # print(USER_ID)

    # Pega os períodos
    period_keys = get_periodos(ACCESS_TOKEN, 2)
    print(period_keys)


    for period_key in period_keys:
        cria_relatorio(ACCESS_TOKEN, period_key)

        arquivo_json = f"../dados/dados_relatorio_{period_key}.json"  # Substitua pelo caminho do seu arquivo JSON
        arquivo_excel = f"../dados/Vendas_Online_{period_key}.xlsx"  # Nome do arquivo Excel de saída
        converter_json_para_excel(arquivo_json, arquivo_excel)



    # order_id = '2000010645139334'
    # response = get_nf_by_order_id(ACCESS_TOKEN, order_id, user_id='276359269')
    # print(response)

    # shipping_id = '44387327300'
    # # shipping_response = get_billing_info(ACCESS_TOKEN, shipping_id)
    # shipping_response = get_all_shipmentts_info(ACCESS_TOKEN, shipping_id)
    # print(shipping_response)



    # order_id = '2000010277939390'
    # response = get_order_by_id(ACCESS_TOKEN, order_id)
    # print(response)


    # Consulta Numero NF e Código de acesso
    # shipping_id = '44494676185'
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