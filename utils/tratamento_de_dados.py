import pandas as pd
import numpy as np
from collections import Counter
import json


def convert_numpy(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    return obj


def cria_dataframe_com_dados_dos_pedidos(data):
    # Tabela principal (uma linha por resultado)
    main_records = []
    sales_records = []

    for item in data['results']:

        if 'sales_info' not in item or item['sales_info'] == "None" or item['sales_info'] is None:
            print(item)
            continue

        # Gerar um ID único para relacionar as tabelas
        result_id = item['charge_info']['detail_id']  # Usando detail_id como identificador único

        # Criar registro principal
        main_record = {
            'result_id': result_id,
            'charge_info_creation_date_time': item['charge_info']['creation_date_time'],
            'charge_info_detail_id': item['charge_info']['detail_id'],
            'charge_info_transaction_detail': item['charge_info']['transaction_detail'],
            'charge_info_detail_amount': item['charge_info']['detail_amount'],
            'discount_info_charge_amount_without_discount': item['discount_info']['charge_amount_without_discount'],
            'discount_info_discount_amount': item['discount_info']['discount_amount'],
            'shipping_info_shipping_id': (item.get('shipping_info') or {}).get('shipping_id', ''),
            'shipping_info_receiver_shipping_cost': (item.get('shipping_info') or {}).get('receiver_shipping_cost', ''),
            'document_info_document_id': item['document_info']['document_id'],
            'marketplace_info_marketplace': item['marketplace_info']['marketplace']
        }
        main_records.append(main_record)

        # Criar registros de vendas relacionados
        for sale in item['sales_info']:
            sale_record = {'result_id': result_id}  # Chave estrangeira
            for key, value in sale.items():
                sale_record[f'sales_info_{key}'] = value
            sales_records.append(sale_record)

    # Criar DataFrames
    df_sales = pd.DataFrame(sales_records)
    df_sales = df_sales[['sales_info_order_id']].drop_duplicates()

    df_main = pd.DataFrame(main_records)

    return df_sales


def consilida_dados_dos_pedidos(arquivo_json, arquivo_json_consolidado):
    # Ler o arquivo JSON
    with open(arquivo_json, 'r', encoding='utf-8') as f:
        dados = json.load(f)

    # Filtrar os dados para remover registros com status "cancelled"
    # dados_filtrados = [item for item in dados if item.get('order_status') != 'cancelled']
    dados_filtrados = dados

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
        item['tipo_documento'] = item.get('cliente_doc_type', None)
        item['no_documento'] = item.get('cliente_doc_number', None)
        if convert_to_float(item.get('invoice_amount', 0)) == 0:
            item['invoice_amount'] = item['paid_amount']


    # Criar um DataFrame com as colunas desejadas e na ordem especificada
    df_consolidado = pd.DataFrame([
        {
            'Nome NF': item['nome_cliente_nf'],
            'Nota': convert_to_int(item['invoice_number']),
            'Valor': convert_to_float(item['invoice_amount']),
            'Banco': convert_to_float(item['invoice_amount']) - convert_to_float(item['frete_empresa']) - convert_to_float(item['marketplace_fee']),
            'Frete/Taxa': convert_to_float(item['frete_empresa']),
            'Mercado Pago': convert_to_float(item['marketplace_fee']),
            'Apelido': item['buyer_nickname'],
            'Frete Cliente': convert_to_float(item['frete_cliente']),
            # 'total_amount': convert_to_float(item['total_amount']),
            # 'paid_amount': convert_to_float(item['paid_amount']),
            'Status': item['order_status'],
            'Order_ID ML': item['order_id'],
            'Tipo de Doc': item['tipo_documento'],
            'No. Doc': item['no_documento'],
            'Cod. Cliente WebMais': None,
            'No. Pedido WebMais': None
        } for item in dados_agrupados
    ])

    # salvar o dataframe em json
    df_consolidado.to_json(arquivo_json_consolidado, orient='records', force_ascii=False, indent=4)

    # Salvar o resultado em um arquivo JSON
    # with open(arquivo_json_consolidado, "w", encoding="utf-8") as f:
    #     json.dump(all_relatorio, f, ensure_ascii=False, indent=4, default=convert_numpy)
