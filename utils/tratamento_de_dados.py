import pandas as pd


def cria_dataframe_com_dados_dos_pedidos(data):
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

    return df_sales

