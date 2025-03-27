import pandas as pd
import numpy as np
import json
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from collections import Counter


# Carregando o JSON (assumindo que você já tem o JSON em uma variável chamada 'data')
# data = json.loads(json_string)


# Carregar os dados do JSON
def converter_json_para_excel(arquivo_json, arquivo_excel):
    # Ler o arquivo JSON
    with open(arquivo_json, 'r', encoding='utf-8') as f:
        dados = json.load(f)

    # Filtrar os dados para remover registros com status "cancelled"
    dados_filtrados = [item for item in dados if item.get('order_status') != 'cancelled']
    # dados_filtrados = dados

    order_ids = [item['order_id'] for item in dados_filtrados]
    repetidos = [item for item, count in Counter(order_ids).items() if count > 1]
    if repetidos:
        print("Existem pedidos com order_ir REPETIROS !!!!", repetidos)

    order_ids = [item['order_id'] for item in dados_filtrados]
    repetidos = [item for item, count in Counter(order_ids).items() if count > 1]
    if repetidos:
        print("Existem pedidos com order_ir REPETIROS !!!!", repetidos)


    # Função para converter valores para float com tratamento de valores vazios e arredondamento para 2 casas decimais
    def convert_to_float(value):
        if value == '' or value is None:
            return 0.00
        try:
            return round(float(value), 2)
        except (ValueError, TypeError):
            return 0.00

    # Função para converter valores para int com tratamento de valores vazios
    def convert_to_int(value):
        if value == '' or value is None:
            return 0
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0

    # Agrupar os dados pelo número da nota fiscal (order_id)
    agrupados = {}
    nao_agrupaveis = []

    for item in dados_filtrados:
        invoice_number = item.get('invoice_number')
        shipping_id = item.get('shipping_id')

        if invoice_number:
            chave = f"inv_{invoice_number}"
        elif shipping_id is not None:
            chave = f"ship_{shipping_id}"
        else:
            nao_agrupaveis.append(item)
            continue

        if chave in agrupados:
            agrupados[chave]['marketplace_fee'] += convert_to_float(item['marketplace_fee'])
            agrupados[chave]['total_amount'] += convert_to_float(item['total_amount'])
            agrupados[chave]['paid_amount'] += convert_to_float(item['paid_amount'])
        else:
            agrupados[chave] = item.copy()
            agrupados[chave]['marketplace_fee'] = convert_to_float(item['marketplace_fee'])
            agrupados[chave]['total_amount'] = convert_to_float(item['total_amount'])
            agrupados[chave]['paid_amount'] = convert_to_float(item['paid_amount'])


    # # Agrupar os dados pelo número do pack_id (pack_id)
    # agrupados2 = {}
    # for item in agrupados:
    #     pack_id = item['pack_id']
    #     order_id = item['order_id']
    #     if pack_id != 0 and pack_id in agrupados2:
    #         # Soma o marketplace_fee para notas fiscais iguais
    #         agrupados2[order_id]['marketplace_fee'] = convert_to_float(agrupados2[order_id]['marketplace_fee']) + convert_to_float(item['marketplace_fee'])
    #     else:
    #         # Cria uma cópia do item para não modificar o original
    #         agrupados2[order_id] = item.copy()

    # Converter o dicionário agrupado de volta para uma lista
    dados_agrupados = list(agrupados.values()) + nao_agrupaveis
    for item in dados_agrupados:
        if convert_to_float(item.get('invoice_amount', 0)) == 0:
            item['invoice_amount'] = item['total_amount']


    # Criar um DataFrame com as colunas desejadas e na ordem especificada
    df = pd.DataFrame([
        {
            'Nome': item['buyer_fullname'],
            'Nota': convert_to_int(item['invoice_number']),
            'Valor': convert_to_float(item['invoice_amount']),
            'Banco': convert_to_float(item['invoice_amount']) - convert_to_float(item['frete_empresa']) - convert_to_float(item['marketplace_fee']),
            'Frete/Taxa': convert_to_float(item['frete_empresa']),
            'Mercado Pago': convert_to_float(item['marketplace_fee']),
            'Apelido': item['buyer_nickname'],
            'Frete Cliente': convert_to_float(item['frete_cliente']),
            # 'total_amount': convert_to_float(item['total_amount']),
            # 'paid_amount': convert_to_float(item['paid_amount']),
            'Status': item['order_status']
        } for item in dados_agrupados
    ])


    # Definir formatos para colunas com valores numéricos
    colunas_numericas = ['C', 'D', 'E', 'F', 'H', 'I', 'J']

    # Salvar os dados em um arquivo Excel
    df.to_excel(arquivo_excel, index=False)

    # Ajustar a formatação das colunas
    ajustar_formatacao_excel(arquivo_excel, colunas_numericas)

    print(f"Arquivo Excel criado com sucesso: {arquivo_excel}")


def ajustar_formatacao_excel(arquivo_excel, colunas_numericas):
    # Carregar o arquivo Excel existente
    wb = load_workbook(arquivo_excel)
    ws = wb.active

    # Ajustar a largura das colunas com base no conteúdo
    for col in range(1, ws.max_column + 1):
        coluna = get_column_letter(col)
        max_length = 0
        for cell in ws[coluna]:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        ws.column_dimensions[coluna].width = adjusted_width

    # Aplicar formato de número nas colunas numéricas
    for row in range(2, ws.max_row + 1):  # Começando da linha 2 para pular o cabeçalho
        for col in colunas_numericas:
            cell = ws[f"{col}{row}"]
            if cell.value is not None:
                cell.number_format = '#0.00'

    # Salvar as alterações
    wb.save(arquivo_excel)
