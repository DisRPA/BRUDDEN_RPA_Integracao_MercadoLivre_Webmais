from utils.banco_de_dados import inserir_ou_atualizar_vendas, consulta_tabela
from utils.acesso_webmais import realiza_baixa_de_notas
from utils.logger import logging
import os
import pandas as pd


def gravar_dados_do_excel_para_no_banco(excel_file_name):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(current_dir)

    excel_file_path = os.path.join(root_dir, 'dados', 'lancamento', excel_file_name)

    # Converters para garantir que campos numéricos sejam lidos como string sem ".0"
    converters = {
        "Order_ID ML": str,
        "No. Doc": lambda x: str(int(x)) if pd.notna(x) else None,
        "Cod. Cliente WebMais": lambda x: str(int(x)) if pd.notna(x) else None,
        "No. Pedido WebMais": lambda x: str(int(x)) if pd.notna(x) else None
    }
    df = pd.read_excel(excel_file_path, converters=converters)
    df = df[df["Nome NF"].notna() & (df["Nome NF"] != "")]

    inserir_ou_atualizar_vendas(df, 'vendas_mercado_livre')


def ler_dados_do_banco_e_realizar_baixas(data_do_saque_mercado_livre, login=False):
    # Ler dados do banco para df
    df_mercado_livre = consulta_tabela('vendas_mercado_livre')

    # filtra apenas registros não lançados
    df_mercado_livre = df_mercado_livre[
        ~(
                (df_mercado_livre['baixa_valor_nota'] == 1) &
                (df_mercado_livre['baixa_valor_mercado_pago'] == 1) &
                (df_mercado_livre['baixa_valor_frete'] == 1)
        )
    ]

    # filtra registros com valores null
    df_mercado_livre = df_mercado_livre[
        ~(
                (df_mercado_livre['Valor'].isna()) &
                (df_mercado_livre['Banco'].isna()) &
                (df_mercado_livre['Frete/Taxa'].isna()) &
                (df_mercado_livre['Mercado Pago'].isna())
        )
    ]

    df_mercado_livre['No. Doc'] = df_mercado_livre['No. Doc'].astype(int)

    if not df_mercado_livre.empty:
        realiza_baixa_de_notas(df_mercado_livre, data_do_saque_mercado_livre, login)
    else:
        logging.info("Nenhum registro novo para ser baixado")


def main(login):

    excel_file_name = 'Vendas Mercado Livre Novembro 2025.xlsx'
    data_do_saque_mercado_livre = '05/01/2026'

    # gravar dados do Excel no banco
    # gravar_dados_do_excel_para_no_banco(excel_file_name)
    # return

    #  google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-playwright --no-first-run --no-default-browser-check --disable-features=MediaRouter --disable-component-update --disable-features=PrivacySandboxSettings4 --disable-sync --disable-features=Translate https://erp2.webmaissistemas.com.br/csp/kelt/system/www/index.csp


    # Realiza as Baixas
    ler_dados_do_banco_e_realizar_baixas(data_do_saque_mercado_livre, login)

    print("fim")



if __name__ == "__main__":
    main(login=True)