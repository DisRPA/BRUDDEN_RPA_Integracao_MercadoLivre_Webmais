"""Prepara o relatório consolidado antes de virar o Excel do cliente.

O relatório do Mercado Livre repete pedidos de meses anteriores (37 dos 276 de
ago/2026). Alguns já foram baixados no WebMais e voltam só para dar trabalho -
foi assim que a NF 51178 escapou da conferência e sumiu em silêncio da fila de
baixa em set/2026.

O que esta etapa faz:
  - TIRA as linhas cujo pedido ML já está baixado no banco (dinheiro fechado);
  - MANTÉM, com aviso na coluna OBS, as linhas com erro na rodada anterior
    (dinheiro em aberto: alguém precisa olhar);
  - MANTÉM, com aviso na OBS, as linhas que o cliente já removeu em um relatório
    anterior;
  - registra no banco a foto do que foi enviado, para saber depois o que o
    cliente tirou na revisão.

Não filtra por Status: existe pedido "cancelled" no ML cuja nota existe e foi
paga (ex.: NF 50731 de jul/2026). Cancelado só sai quando o cliente tira.
"""

import pandas as pd

from utils.banco_de_dados import (
    consulta_tabela,
    consulta_removidos_pelo_cliente,
    registrar_relatorio_enviado,
)
from utils.logger import logging


def _listar_notas(df, limite=40):
    notas = sorted({str(valor) for valor in df['Nota']})
    if not notas:
        return "(nenhuma)"
    if len(notas) > limite:
        return ", ".join(notas[:limite]) + f" ... (+{len(notas) - limite})"
    return ", ".join(notas)


def preparar_relatorio_para_o_cliente(arquivo_json_consolidado, arquivo_json_cliente, period_key):
    df = pd.read_json(arquivo_json_consolidado, orient='records', dtype={'Order_ID ML': str})
    df['Order_ID ML'] = df['Order_ID ML'].astype(str)
    total_inicial = len(df)

    banco = consulta_tabela('vendas_mercado_livre')
    banco['Order_ID ML'] = banco['Order_ID ML'].astype(str)

    concluidos = banco[
        (banco['baixa_valor_nota'] == 1)
        & (banco['baixa_valor_mercado_pago'] == 1)
        & (banco['baixa_valor_frete'] == 1)
        & (banco['erro'] == 0)
    ]
    ids_baixados = set(concluidos['Order_ID ML'])

    com_erro = banco[banco['erro'] == 1]
    erros_por_pedido = dict(zip(com_erro['Order_ID ML'], com_erro['descricao_erro']))

    removidos_antes = consulta_removidos_pelo_cliente()

    if 'OBS' not in df.columns:
        df['OBS'] = ""
    df['OBS'] = df['OBS'].fillna("")

    # 1) Avisa sobre erro em rodada anterior (a linha continua no relatório).
    marca_erro = df['Order_ID ML'].isin(erros_por_pedido)
    for indice in df.index[marca_erro]:
        descricao = erros_por_pedido.get(df.at[indice, 'Order_ID ML']) or "sem descrição"
        df.at[indice, 'OBS'] = (
            f"ATENÇÃO - erro no relatório do mês anterior: {descricao}"
        )

    # 2) Avisa sobre linha que o cliente já tirou antes (a linha continua no relatório).
    marca_removido = df['Order_ID ML'].isin(removidos_antes) & ~marca_erro
    for indice in df.index[marca_removido]:
        periodo = removidos_antes.get(df.at[indice, 'Order_ID ML'])
        df.at[indice, 'OBS'] = (
            f"ATENÇÃO - linha removida por você na revisão do relatório de {periodo}"
        )

    # 3) Tira o que já foi baixado (dinheiro fechado, nada a conferir).
    ja_baixados = df[df['Order_ID ML'].isin(ids_baixados)]
    df_final = df[~df['Order_ID ML'].isin(ids_baixados)].copy()

    logging.info(
        f"Relatório {period_key}: {total_inicial} linha(s) consolidadas; "
        f"{len(ja_baixados)} retirada(s) por já estar(em) baixada(s); "
        f"{len(df_final)} linha(s) enviadas ao cliente."
    )
    if not ja_baixados.empty:
        logging.info(f"Retiradas por já estarem baixadas: notas {_listar_notas(ja_baixados)}")
    if marca_erro.any():
        logging.info(
            f"{int(marca_erro.sum())} linha(s) mantidas com aviso de erro anterior: "
            f"notas {_listar_notas(df[marca_erro])}"
        )
    if marca_removido.any():
        logging.info(
            f"{int(marca_removido.sum())} linha(s) mantidas com aviso de remoção anterior: "
            f"notas {_listar_notas(df[marca_removido])}"
        )

    registrar_relatorio_enviado(df_final, period_key)

    df_final.to_json(arquivo_json_cliente, orient='records', force_ascii=False, indent=4)
    return df_final
