import requests
import json
from dotenv import load_dotenv
from utils.ml_autenticacao import atualizar_token_com_refresh_token
from utils.gera_excel import converter_json_para_excel
from utils.tratamento_de_dados import cria_dataframe_com_dados_dos_pedidos, consilida_dados_dos_pedidos
from utils.api_mercado_livre import consulta_pedido_por_pedido, get_periodos, get_user_id, get_order_by_period, consulta_dados_cliente, get_billing_info
from utils.api_mercadolivre_testes import get_nf_by_order_id, get_all_shipmentts_info
from utils.acesso_webmais import consulta_numero_nf_por_doc_cliente
from utils.relatorio_para_cliente import preparar_relatorio_para_o_cliente
import os
from datetime import datetime, timezone
import subprocess


load_dotenv()


def cria_relatorio(ACCESS_TOKEN, period_key):

    response = get_order_by_period(ACCESS_TOKEN, period_key)
    # print(response)

    df_pedidos = cria_dataframe_com_dados_dos_pedidos(response)  # retorna lista de orders

    # Consulta pedido por pedido e salva todos no arquivo pedidos.json
    consulta_pedido_por_pedido(ACCESS_TOKEN, df_pedidos, period_key)


def main(passo):
    # period_keys = get_periodos(os.getenv("ML_ACCESSTOKEN"), 2)

    if passo != 2:
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

    # shipping_id = '44514909514'
    # response = get_billing_info(ACCESS_TOKEN, shipping_id)
    # print(response)
    #
    # order_id = '2000011055531640'
    # response = consulta_dados_cliente(ACCESS_TOKEN, order_id)
    # print(response)
    #
    # shipping_id = '44514719410'
    # # shipping_response = get_billing_info(ACCESS_TOKEN, shipping_id)
    # shipping_response = get_all_shipmentts_info(ACCESS_TOKEN, shipping_id)
    # print(shipping_response)


    # USER_ID = get_user_id(ACCESS_TOKEN)  # Você pode obter esse ID com /users/me
    # print(USER_ID)

    # Pega os períodos
    # period_keys = get_periodos(ACCESS_TOKEN, 2)
    # print(period_keys)
    period_keys = ['2026-08-01']

    for period_key in period_keys:

        if passo != 2:
            # Passo 1 !!!
            cria_relatorio(ACCESS_TOKEN, period_key)

        arquivo_json = f"../dados/dados_relatorio_{period_key}.json"  # Substitua pelo caminho do seu arquivo JSON
        arquivo_json_consolidado = f"../dados/dados_relatorio_consolidado_{period_key}.json"  # Substitua pelo caminho do seu arquivo JSON
        # O consolidado guarda TUDO (auditoria). O "para_cliente" é o consolidado já
        # sem as notas baixadas e com os avisos na coluna OBS - é ele que vira Excel.
        arquivo_json_para_cliente = f"../dados/dados_relatorio_para_cliente_{period_key}.json"
        arquivo_excel = f"../dados/Vendas_Online_{period_key}.xlsx"  # Nome do arquivo Excel de saída

        if passo != 1:
            # Passo 2 !!!
            # Cria o json consolidado
            # google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-playwright
            # https://erp2.webmaissistemas.com.br/csp/kelt/system/www/index.csp

            proc = subprocess.Popen(
                "bash -ic 'brudden'",
                shell=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            input("Clique quando o browser abrir:")


            print("consolida dados dos pedidos!!")
            consilida_dados_dos_pedidos(arquivo_json, arquivo_json_consolidado)
            print("consulta numero nf por doc")
            consulta_numero_nf_por_doc_cliente(arquivo_json_consolidado)
            print("prepara relatorio para o cliente")
            preparar_relatorio_para_o_cliente(arquivo_json_consolidado, arquivo_json_para_cliente, period_key)
            print("converte json para excel")
            converter_json_para_excel(arquivo_json_para_cliente, arquivo_excel)



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


if __name__ == "__main__":
    # passo = 1 > consulta tudo no mercado livre
    # passo = 2 > Compila os dados
    # >> iniciar pelo termina:
    # google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-playwright --window-size=1380,820 --window-position=500,0 --no-first-run --no-default-browser-check --disable-features=MediaRouter,PrivacySandboxSettings4,Translate --disable-component-update --disable-sync https://erp2.webmaissistemas.com.br/csp/kelt/system/www/index.csp
    # passo com outro valor, executa ambos
    passo = 2

    main(passo)