from utils.banco_de_dados import inserir_na_tabela, consulta_tabela
from utils.acesso_webmais import realiza_baixa_de_notas
import os
import pandas as pd


def gravar_dados_do_excel_para_no_banco():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(current_dir)

    excel_file_name = 'Vendas_Online_Lancamento.xlsx'
    excel_file_path = os.path.join(root_dir, 'dados', 'lancamento', excel_file_name)

    df = pd.read_excel(excel_file_path, sheet_name="ABA CORRIGIDA", converters={"Order_ID ML": str})
    df = df[df["Nome NF"].notna() & (df["Nome NF"] != "")]

    inserir_na_tabela(df, 'vendas_mercado_livre')


def main():


    data_do_saque_mercado_livre = '02/04/2025'

    # gravar dados do Excel no banco
    # gravar_dados_do_excel_para_no_banco()

    # Ler dados do banco para df
    df_mercado_livre = consulta_tabela('vendas_mercado_livre')

    realiza_baixa_de_notas(df_mercado_livre, data_do_saque_mercado_livre)

    print("fim")



if __name__ == "__main__":
    main()