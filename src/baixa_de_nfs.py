from utils.banco_de_dados import inserir_ou_atualizar_vendas, consulta_tabela
from utils.acesso_webmais import realiza_baixa_de_notas
from utils.logger import logging
import os
import pandas as pd


COLUNAS_CHAVE_DUPLICIDADE = ["Nome NF", "Nota", "Order_ID ML"]


def _formatar_identificador(valor):
    if pd.isna(valor):
        return "(vazio)"
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor)


def _formatar_moeda(valor):
    if pd.isna(valor):
        return "(vazio)"
    try:
        valor_formatado = f"{float(valor):,.2f}"
    except (TypeError, ValueError):
        return str(valor)
    return f"R$ {valor_formatado.replace(',', 'X').replace('.', ',').replace('X', '.')}"


def validar_duplicidades_antes_de_gravar(df, excel_file_name):
    """Interrompe a importação se a chave única do SQLite estiver repetida."""
    colunas_ausentes = [
        coluna for coluna in COLUNAS_CHAVE_DUPLICIDADE
        if coluna not in df.columns
    ]
    if colunas_ausentes:
        raise ValueError(
            "Não foi possível validar duplicidades. Coluna(s) ausente(s) no Excel: "
            + ", ".join(colunas_ausentes)
        )

    mascara_duplicados = df.duplicated(
        subset=COLUNAS_CHAVE_DUPLICIDADE,
        keep=False,
    )
    duplicados = df.loc[mascara_duplicados].copy()
    if duplicados.empty:
        return

    # O índice começa em zero e a primeira linha do Excel contém o cabeçalho.
    duplicados["_linha_excel"] = duplicados.index + 2
    detalhes = []
    grupos = duplicados.groupby(
        COLUNAS_CHAVE_DUPLICIDADE,
        dropna=False,
        sort=False,
    )

    for chave, grupo in grupos:
        nome_nf, nota, order_id = chave
        detalhes.append(
            "- Duplicidade: "
            f"Nome NF={_formatar_identificador(nome_nf)}; "
            f"Nota={_formatar_identificador(nota)}; "
            f"Order_ID ML={_formatar_identificador(order_id)}"
        )
        for _, registro in grupo.iterrows():
            status = registro.get("Status")
            status_texto = (
                f"; Status={_formatar_identificador(status)}"
                if not pd.isna(status)
                else ""
            )
            detalhes.append(
                f"  Linha {int(registro['_linha_excel'])}: "
                f"Valor={_formatar_moeda(registro.get('Valor'))}; "
                f"Banco={_formatar_moeda(registro.get('Banco'))}; "
                f"Mercado Pago={_formatar_moeda(registro.get('Mercado Pago'))}; "
                f"Frete/Taxa={_formatar_moeda(registro.get('Frete/Taxa'))}"
                f"{status_texto}"
            )

    mensagem = (
        f"Foram encontradas {grupos.ngroups} duplicidade(s) no arquivo "
        f"'{excel_file_name}', envolvendo {len(duplicados)} linha(s).\n"
        "A gravação no banco foi cancelada. Corrija o arquivo antes de executar "
        "novamente.\n"
        + "\n".join(detalhes)
    )
    logging.error(mensagem)
    raise ValueError(mensagem)


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

    validar_duplicidades_antes_de_gravar(df, excel_file_name)

    inserir_ou_atualizar_vendas(df, 'vendas_mercado_livre')


def ler_dados_do_banco_e_realizar_baixas(data_do_saque_mercado_livre):
    # Ler dados do banco para df
    df_mercado_livre = consulta_tabela('vendas_mercado_livre')

    # filtra apenas registros não lançados
    df_mercado_livre = df_mercado_livre[
        ~(
                (df_mercado_livre['baixa_valor_nota'] == 1) &
                (df_mercado_livre['baixa_valor_mercado_pago'] == 1) &
                (df_mercado_livre['baixa_valor_frete'] == 1) &
                (df_mercado_livre['erro'] == 0)
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
        realiza_baixa_de_notas(df_mercado_livre, data_do_saque_mercado_livre)
    else:
        logging.info("Nenhum registro novo para ser baixado")


def main(tipo):

    excel_file_name = 'Vendas_Online_2026-06-01_JUNHO.xlsx'
    data_do_saque_mercado_livre = '17/07/2026'

    # gravar dados do Excel no banco
    if tipo == 1:
        gravar_dados_do_excel_para_no_banco(excel_file_name)


    # Realiza as Baixas
    if tipo == 2:
        #  google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-playwright --no-first-run --no-default-browser-check --disable-features=MediaRouter --disable-component-update --disable-features=PrivacySandboxSettings4 --disable-sync --disable-features=Translate https://erp2.webmaissistemas.com.br/csp/kelt/system/www/index.csp
        ler_dados_do_banco_e_realizar_baixas(data_do_saque_mercado_livre)

    print("fim")



if __name__ == "__main__":
    # Realiza as Baixas
    tipo = 2

    # gravar dados do Excel no banco
    # tipo = 1

    main(tipo)
