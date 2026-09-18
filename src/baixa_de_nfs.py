from utils.banco_de_dados import (
    inserir_ou_atualizar_vendas,
    consulta_tabela,
    registrar_conferencia_do_cliente,
)
from utils.acesso_webmais import realiza_baixa_de_notas
from utils.logger import logging
import os
import re
import pandas as pd
import subprocess


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


def validar_notas_em_varias_linhas(df, excel_file_name):
    """Interrompe a importação se a mesma nota aparecer em mais de uma linha.

    O WebMais tem um saldo só por nota: a primeira linha baixa o valor inteiro e as
    seguintes ficam sem saldo ("Nota X não encontrada no WebMais"). Pior, o rateio
    entre Banco, Mercado Pago e Frete/Taxa sai errado, porque cada linha traz apenas
    a parte do seu pedido ML - e como a soma dos três ainda fecha com o saldo da nota,
    a baixa é aceita sem acusar divergência. Consolide a nota em uma única linha,
    somando as colunas de valor.
    """
    if "Nota" not in df.columns:
        raise ValueError(
            "Não foi possível validar notas repetidas. Coluna 'Nota' ausente no Excel."
        )

    notas = df["Nota"].map(_formatar_identificador)
    considerar = ~notas.isin(["(vazio)", "0"])
    repetidas = notas[considerar].duplicated(keep=False)

    linhas_repetidas = df.loc[considerar].loc[repetidas].copy()
    if linhas_repetidas.empty:
        return

    # O índice começa em zero e a primeira linha do Excel contém o cabeçalho.
    linhas_repetidas["_linha_excel"] = linhas_repetidas.index + 2
    linhas_repetidas["_nota"] = notas.loc[linhas_repetidas.index]

    detalhes = []
    grupos = linhas_repetidas.groupby("_nota", sort=False)
    for nota, grupo in grupos:
        detalhes.append(f"- Nota {nota} aparece em {len(grupo)} linhas:")
        for _, registro in grupo.iterrows():
            detalhes.append(
                f"  Linha {int(registro['_linha_excel'])}: "
                f"Order_ID ML={_formatar_identificador(registro.get('Order_ID ML'))}; "
                f"Valor={_formatar_moeda(registro.get('Valor'))}; "
                f"Banco={_formatar_moeda(registro.get('Banco'))}; "
                f"Mercado Pago={_formatar_moeda(registro.get('Mercado Pago'))}; "
                f"Frete/Taxa={_formatar_moeda(registro.get('Frete/Taxa'))}"
            )
        detalhes.append(
            "  Consolidado (usar em uma única linha): "
            f"Valor={_formatar_moeda(grupo['Valor'].sum())}; "
            f"Banco={_formatar_moeda(grupo['Banco'].sum())}; "
            f"Mercado Pago={_formatar_moeda(grupo['Mercado Pago'].sum())}; "
            f"Frete/Taxa={_formatar_moeda(grupo['Frete/Taxa'].sum())}"
        )

    mensagem = (
        f"Foram encontradas {grupos.ngroups} nota(s) repetida(s) em mais de uma linha "
        f"no arquivo '{excel_file_name}'.\n"
        "A gravação no banco foi cancelada. Consolide cada nota em uma única linha "
        "antes de executar novamente.\n"
        + "\n".join(detalhes)
    )
    logging.error(mensagem)
    raise ValueError(mensagem)


def ler_excel_de_lancamento(excel_file_name):
    """Lê o Excel de dados/lancamento/ já sem as linhas vazias."""
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
    return df[df["Nome NF"].notna() & (df["Nome NF"] != "")]


def _periodo_do_arquivo(excel_file_name):
    """Tira o período do nome: 'Vendas_Online_2026-08-01_AGOSTO.xlsx' -> '2026-08-01'."""
    achado = re.search(r"\d{4}-\d{2}-\d{2}", excel_file_name)
    return achado.group(0) if achado else None


def registrar_o_que_o_cliente_removeu(df, excel_file_name):
    """Compara o Excel revisado com o relatório que foi enviado ao cliente.

    É aqui que a remoção de linhas canceladas fica registrada. Não dá para
    filtrar cancelado na geração do relatório: existe pedido "cancelled" no ML
    cuja nota existe e foi paga (ex.: NF 50731 de jul/2026). Quem decide é o
    cliente - este passo só aprende a decisão dele e guarda no banco, para a
    linha não voltar sem aviso no relatório do mês seguinte.
    """
    periodo = _periodo_do_arquivo(excel_file_name)
    if not periodo:
        logging.warning(
            f"Não achei o período no nome do arquivo '{excel_file_name}'. "
            "A conferência do cliente não foi registrada."
        )
        return

    if "Order_ID ML" not in df.columns:
        logging.warning(
            "Coluna 'Order_ID ML' ausente no Excel. "
            "A conferência do cliente não foi registrada."
        )
        return

    removidos = registrar_conferencia_do_cliente(periodo, df["Order_ID ML"])
    if removidos is None:
        return

    if removidos.empty:
        logging.info(
            f"Revisão do cliente no período {periodo}: nenhuma linha removida."
        )
        return

    logging.info(
        f"Revisão do cliente no período {periodo}: {len(removidos)} linha(s) removida(s)."
    )
    for _, registro in removidos.iterrows():
        logging.info(
            f"  Removida pelo cliente: Nota={_formatar_identificador(registro['Nota'])}; "
            f"Nome NF={registro['Nome NF']}; "
            f"Valor={_formatar_moeda(registro['Valor'])}; "
            f"Status={registro['Status']}; "
            f"Order_ID ML={registro['Order_ID ML']}"
        )


def gravar_dados_do_excel_para_no_banco(excel_file_name):
    df = ler_excel_de_lancamento(excel_file_name)

    validar_duplicidades_antes_de_gravar(df, excel_file_name)
    validar_notas_em_varias_linhas(df, excel_file_name)

    registrar_o_que_o_cliente_removeu(df, excel_file_name)

    inserir_ou_atualizar_vendas(df, 'vendas_mercado_livre')


def _listar_notas(df, limite=40):
    """Notas de um DataFrame em texto curto, para caber no log."""
    notas = sorted({_formatar_identificador(valor) for valor in df['Nota']})
    if not notas:
        return "(nenhuma)"
    if len(notas) > limite:
        return ", ".join(notas[:limite]) + f" ... (+{len(notas) - limite})"
    return ", ".join(notas)


def _chaves_unicas(df):
    """Chave única da tabela, normalizada, para comparar banco com Excel."""
    return {
        tuple(_formatar_identificador(registro[coluna]) for coluna in COLUNAS_CHAVE_DUPLICIDADE)
        for _, registro in df.iterrows()
    }


def logar_composicao_da_fila(df_banco, df_fila, df_sem_valores, excel_file_name=None):
    """Explica no log quem entrou e quem ficou de fora da fila de baixa.

    A baixa lê o banco inteiro, não o Excel da rodada. Sem este resumo, linhas do
    arquivo que já foram baixadas em rodadas anteriores somem em silêncio e notas
    velhas com erro aparecem do nada - foi o que confundiu a conferência de set/2026.
    """
    concluidos = len(df_banco) - len(df_fila) - len(df_sem_valores)
    logging.info(
        f"Fila de baixa: {len(df_fila)} registro(s). "
        f"Banco tem {len(df_banco)} registro(s); "
        f"{concluidos} já concluído(s) em rodadas anteriores (pulados)."
    )

    com_erro = df_fila[df_fila['erro'] == 1]
    if not com_erro.empty:
        logging.info(
            f"{len(com_erro)} registro(s) voltaram por erro de rodada anterior: "
            f"notas {_listar_notas(com_erro)}"
        )

    if not df_sem_valores.empty:
        logging.info(
            f"{len(df_sem_valores)} registro(s) fora da fila por não ter valores: "
            f"notas {_listar_notas(df_sem_valores)}"
        )

    if not excel_file_name:
        return

    try:
        df_excel = ler_excel_de_lancamento(excel_file_name)
    except Exception as e:
        logging.warning(
            f"Não foi possível comparar a fila com o arquivo '{excel_file_name}': {e}"
        )
        return

    chaves_fila = _chaves_unicas(df_fila) | _chaves_unicas(df_sem_valores)
    fora_da_fila = df_excel[[
        tuple(_formatar_identificador(registro[coluna]) for coluna in COLUNAS_CHAVE_DUPLICIDADE)
        not in chaves_fila
        for _, registro in df_excel.iterrows()
    ]]

    logging.info(
        f"Arquivo '{excel_file_name}': {len(df_excel)} linha(s); "
        f"{len(df_excel) - len(fora_da_fila)} na fila; "
        f"{len(fora_da_fila)} fora da fila (já baixada(s) antes)."
    )
    if not fora_da_fila.empty:
        logging.info(
            f"Linhas do arquivo fora da fila: notas {_listar_notas(fora_da_fila)}"
        )


def ler_dados_do_banco_e_realizar_baixas(data_do_saque_mercado_livre, excel_file_name=None):
    # Ler dados do banco para df
    df_banco = consulta_tabela('vendas_mercado_livre')

    # filtra apenas registros não lançados
    df_mercado_livre = df_banco[
        ~(
                (df_banco['baixa_valor_nota'] == 1) &
                (df_banco['baixa_valor_mercado_pago'] == 1) &
                (df_banco['baixa_valor_frete'] == 1) &
                (df_banco['erro'] == 0)
        )
    ]

    # filtra registros com valores null
    sem_valores = (
            (df_mercado_livre['Valor'].isna()) &
            (df_mercado_livre['Banco'].isna()) &
            (df_mercado_livre['Frete/Taxa'].isna()) &
            (df_mercado_livre['Mercado Pago'].isna())
    )
    df_sem_valores = df_mercado_livre[sem_valores]
    df_mercado_livre = df_mercado_livre[~sem_valores].copy()

    logar_composicao_da_fila(df_banco, df_mercado_livre, df_sem_valores, excel_file_name)

    df_mercado_livre['No. Doc'] = df_mercado_livre['No. Doc'].astype(int)

    if not df_mercado_livre.empty:
        realiza_baixa_de_notas(df_mercado_livre, data_do_saque_mercado_livre)
    else:
        logging.info("Nenhum registro novo para ser baixado")


def main(tipo):

    excel_file_name = 'Vendas_Online_2026-08-01_AGOSTO.xlsx'
    data_do_saque_mercado_livre = '15/09/2026'

    # gravar dados do Excel no banco
    if tipo == 1:
        gravar_dados_do_excel_para_no_banco(excel_file_name)


    # Realiza as Baixas
    if tipo == 2:
        #  google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-playwright --no-first-run --no-default-browser-check --disable-features=MediaRouter --disable-component-update --disable-features=PrivacySandboxSettings4 --disable-sync --disable-features=Translate https://erp2.webmaissistemas.com.br/csp/kelt/system/www/index.csp
        proc = subprocess.Popen(
            "bash -ic 'brudden'",
            shell=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        input("Digite algo para seguir quando o browser abrir:")


        ler_dados_do_banco_e_realizar_baixas(data_do_saque_mercado_livre, excel_file_name)

    print("fim")



if __name__ == "__main__":
    # Desativa suspensão da tela
    subprocess.run(["xset", "-dpms"])
    subprocess.run(["xset", "s", "off"])

    try:
        # Realiza as Baixas
        tipo = 2

        # gravar dados do Excel no banco
        # tipo = 1

        main(tipo)
    finally:
        # Reativa comportamento padrão ao sair
        subprocess.run(["xset", "+dpms"])
        subprocess.run(["xset", "s", "on"])
        # os.killpg(proc1.pid, signal.SIGTERM)