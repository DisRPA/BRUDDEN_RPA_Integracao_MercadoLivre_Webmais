import pandas as pd
import numpy as np
import json
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

# Carregando o JSON (assumindo que você já tem o JSON em uma variável chamada 'data')
# data = json.loads(json_string)

def cria_excel(data):
    # Tabela principal (uma linha por resultado)
    main_records = []
    sales_records = []

    for item in data['results']:
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


    # Exportar para Excel (em abas diferentes)
    with pd.ExcelWriter('../dados/dados_vendas_relacionais.xlsx') as writer:
        df_main.to_excel(writer, sheet_name='Resultados', index=False)


    return df_sales


# Carregar os dados do JSON
def converter_json_para_excel(arquivo_json, arquivo_excel):
    # Ler o arquivo JSON
    with open(arquivo_json, 'r', encoding='utf-8') as f:
        dados = json.load(f)

    # Filtrar os dados para remover registros com status "cancelled"
    dados_filtrados = [item for item in dados if item.get('order_status') != 'cancelled']

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

    # Agrupar os dados pelo número da nota fiscal (invoice_number)
    agrupados = {}
    for item in dados_filtrados:
        invoice_num = item['invoice_number']
        if invoice_num in agrupados:
            # Soma o marketplace_fee para notas fiscais iguais
            agrupados[invoice_num]['marketplace_fee'] = convert_to_float(
                agrupados[invoice_num]['marketplace_fee']) + convert_to_float(item['marketplace_fee'])
        else:
            # Cria uma cópia do item para não modificar o original
            agrupados[invoice_num] = item.copy()

    # Converter o dicionário agrupado de volta para uma lista
    dados_agrupados = list(agrupados.values())

    # Criar um DataFrame com as colunas desejadas e na ordem especificada
    df = pd.DataFrame([
        {
            'Nome': item['buyer_fullname'],
            'Nota': convert_to_int(item['invoice_number']),
            'Valor': convert_to_float(item['invoice_amount']),
            'Banco': convert_to_float(item['invoice_amount']) - convert_to_float(
                item['frete_empresa']) - convert_to_float(item['marketplace_fee']),
            'Frete/Taxa': convert_to_float(item['frete_empresa']),
            'Mercado Pago': convert_to_float(item['marketplace_fee']),
            'Apelido': item['buyer_nickname'],
            'Frete Cliente': convert_to_float(item['frete_cliente'])
        } for item in dados_agrupados
    ])

    # Salvar os dados em um arquivo Excel
    df.to_excel(arquivo_excel, index=False)

    # Ajustar a formatação das colunas
    ajustar_formatacao_excel(arquivo_excel)

    print(f"Arquivo Excel criado com sucesso: {arquivo_excel}")


def ajustar_formatacao_excel(arquivo_excel):
    # Carregar o arquivo Excel existente
    wb = load_workbook(arquivo_excel)
    ws = wb.active

    # Definir formatos para colunas com valores numéricos
    colunas_numericas = ['C', 'D', 'E', 'F', 'H']  # Valor, Banco, Frete/Taxa, Mercado Pago, Frete Cliente

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
