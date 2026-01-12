import pandas as pd
import json
from datetime import datetime


# Função para carregar o JSON
def carregar_json(arquivo_json=None, json_string=None):
    """
    Carrega o JSON a partir de um arquivo ou string
    """
    if arquivo_json:
        with open(arquivo_json, 'r', encoding='utf-8') as file:
            return json.load(file)
    elif json_string:
        return json.loads(json_string)
    else:
        raise ValueError("É necessário fornecer um arquivo JSON ou uma string JSON")


# Função para normalizar datas
def normalizar_data(data_str):
    """
    Converte strings de data para formato datetime padrão
    """
    if data_str is None or data_str == "None":
        return None
    try:
        # Tentar parse da data (removendo o timezone)
        data_str = data_str.split(".")[0]
        return datetime.strptime(data_str, "%Y-%m-%dT%H:%M:%S")
    except:
        return data_str


# Função para normalizar valores
def normalizar_valor(valor):
    """
    Normaliza valores para evitar problemas com "None" como string
    """
    if valor == "None":
        return None
    return valor


# Função principal para processar o JSON e criar tabelas relacionadas
def processar_json_para_tabelas(dados):
    """
    Processa o JSON e cria um dicionário de DataFrames para tabelas relacionadas
    """
    # Verificar se há dados válidos
    if dados is None:
        return {}

    # Dicionário para armazenar todos os DataFrames
    tabelas = {}

    # Tabela principal (pedidos)
    pedido = {
        'id': dados['id'],
        'invoice_number': dados.get('invoice_number', ''),
        'date_created': normalizar_data(dados['date_created']),
        'last_updated': normalizar_data(dados['last_updated']),
        'date_closed': normalizar_data(dados['date_closed']),
        'pack_id': normalizar_valor(dados['pack_id']),
        'fulfilled': dados['fulfilled'],
        'buying_mode': dados['buying_mode'],
        'shipping_cost': normalizar_valor(dados['shipping_cost']),
        'total_amount': dados['total_amount'],
        'paid_amount': dados['paid_amount'],
        'currency_id': dados['currency_id'],
        'status': dados['status'],
        'status_detail': normalizar_valor(dados['status_detail']),
        'seller_id': dados['seller']['id'],
        'buyer_id': dados['buyer']['id'],
        'buyer_nickname': dados['buyer'].get('nickname', ''),
        'buyer_first_name': dados['buyer'].get('first_name', ''),
        'buyer_last_name': dados['buyer'].get('last_name', ''),
        'taxes_amount': dados['taxes']['amount'],
        'taxes_currency_id': dados['taxes']['currency_id'],
        'taxes_id': normalizar_valor(dados['taxes']['id']),
        'manufacturing_ending_date': normalizar_valor(dados['manufacturing_ending_date']),
        'context_channel': dados['context']['channel'],
        'context_site': dados['context']['site'],
        'shipping_id': dados['shipping']['id'] if 'id' in dados['shipping'] else None

    }

    # Adicionar detalhes de cancelamento se existirem
    if dados['cancel_detail'] and dados['cancel_detail'] != "None":
        pedido.update({
            'cancel_detail_group': dados['cancel_detail']['group'],
            'cancel_detail_code': dados['cancel_detail']['code'],
            'cancel_detail_description': dados['cancel_detail']['description'],
            'cancel_detail_requested_by': dados['cancel_detail']['requested_by'],
            'cancel_detail_date': normalizar_data(dados['cancel_detail']['date']),
            'cancel_detail_application_id': dados['cancel_detail']['application_id']
        })

    # Criar DataFrame de pedidos
    tabelas['pedidos'] = pd.DataFrame([pedido])

    # Tabela de tags
    if dados['tags'] and dados['tags'] != "None":
        tags = []
        for tag in dados['tags']:
            tags.append({
                'pedido_id': dados['id'],
                'tag': tag
            })
        tabelas['tags'] = pd.DataFrame(tags)

    # Tabela de mediações
    if dados['mediations'] and dados['mediations'] != "None":
        mediacoes = []
        for mediacao in dados['mediations']:
            mediacoes.append({
                'pedido_id': dados['id'],
                'mediacao_id': mediacao['id']
            })
        tabelas['mediacoes'] = pd.DataFrame(mediacoes)

    # Tabela de itens de pedido
    if dados['order_items'] and dados['order_items'] != "None":
        itens = []
        atributos_variacao = []

        for idx, item in enumerate(dados['order_items']):
            # ID único para o item dentro do pedido
            item_id = f"{dados['id']}_{idx}"

            # Dados principais do item
            item_dict = {
                'item_id': item_id,
                'pedido_id': dados['id'],
                'product_id': item['item']['id'],
                'title': item['item']['title'],
                'category_id': item['item']['category_id'],
                'variation_id': normalizar_valor(item['item']['variation_id']),
                'seller_custom_field': normalizar_valor(item['item']['seller_custom_field']),
                'warranty': item['item']['warranty'],
                'condition': item['item']['condition'],
                'seller_sku': item['item']['seller_sku'],
                'global_price': normalizar_valor(item['item']['global_price']),
                'net_weight': normalizar_valor(item['item']['net_weight']),
                'user_product_id': item['item']['user_product_id'],
                'release_date': normalizar_valor(item['item']['release_date']),
                'quantity': item['quantity'],
                'requested_quantity_value': item['requested_quantity']['value'],
                'requested_quantity_measure': item['requested_quantity']['measure'],
                'picked_quantity': normalizar_valor(item['picked_quantity']),
                'unit_price': item['unit_price'],
                'full_unit_price': item['full_unit_price'],
                'full_unit_price_currency_id': item['full_unit_price_currency_id'],
                'currency_id': item['currency_id'],
                'manufacturing_days': normalizar_valor(item['manufacturing_days']),
                'sale_fee': item['sale_fee'],
                'listing_type_id': item['listing_type_id'],
                'base_exchange_rate': normalizar_valor(item['base_exchange_rate']),
                'base_currency_id': normalizar_valor(item['base_currency_id']),
                'element_id': normalizar_valor(item['element_id']),
                'discounts': normalizar_valor(item['discounts']),
                'bundle': normalizar_valor(item['bundle']),
                'compat_id': normalizar_valor(item['compat_id']),
                'stock': normalizar_valor(item['stock']),
                'kit_instance_id': normalizar_valor(item['kit_instance_id'])
            }
            itens.append(item_dict)

            # Tabela de atributos de variação se existirem
            if 'variation_attributes' in item['item'] and item['item']['variation_attributes'] and item['item'][
                'variation_attributes'] != "None" and len(item['item']['variation_attributes']) > 0:
                for atributo in item['item']['variation_attributes']:
                    if isinstance(atributo, dict) and 'id' in atributo and 'value_name' in atributo:
                        atr = {
                            'item_id': item_id,
                            'atributo_id': atributo['id'],
                            'nome': atributo.get('name', None),
                            'valor_nome': atributo['value_name'],
                            'valor_id': atributo.get('value_id', None)
                        }
                        atributos_variacao.append(atr)

        tabelas['itens_pedido'] = pd.DataFrame(itens)
        if atributos_variacao:
            tabelas['atributos_variacao'] = pd.DataFrame(atributos_variacao)

    # Tabela de pagamentos
    if dados['payments'] and dados['payments'] != "None":
        pagamentos = []
        acoes_disponiveis = []

        for pagamento in dados['payments']:
            # Dados principais do pagamento
            pagamento_dict = {
                'pagamento_id': pagamento['id'],
                'pedido_id': pagamento['order_id'],
                'payer_id': pagamento['payer_id'],
                'collector_id': pagamento['collector']['id'],
                'card_id': pagamento['card_id'],
                'reason': pagamento['reason'],
                'site_id': pagamento['site_id'],
                'payment_method_id': pagamento['payment_method_id'],
                'currency_id': pagamento['currency_id'],
                'installments': pagamento['installments'],
                'issuer_id': pagamento['issuer_id'],
                'coupon_id': normalizar_valor(pagamento['coupon_id']),
                'activation_uri': normalizar_valor(pagamento['activation_uri']),
                'operation_type': pagamento['operation_type'],
                'payment_type': pagamento['payment_type'],
                'status': pagamento['status'],
                'status_code': normalizar_valor(pagamento['status_code']),
                'status_detail': pagamento['status_detail'],
                'transaction_amount': pagamento['transaction_amount'],
                'transaction_amount_refunded': pagamento['transaction_amount_refunded'],
                'taxes_amount': pagamento['taxes_amount'],
                'shipping_cost': pagamento['shipping_cost'],
                'coupon_amount': pagamento['coupon_amount'],
                'overpaid_amount': pagamento['overpaid_amount'],
                'total_paid_amount': pagamento['total_paid_amount'],
                'installment_amount': pagamento['installment_amount'],
                'deferred_period': normalizar_valor(pagamento['deferred_period']),
                'date_approved': normalizar_data(pagamento['date_approved']),
                'transaction_order_id': normalizar_valor(pagamento['transaction_order_id']),
                'date_created': normalizar_data(pagamento['date_created']),
                'date_last_modified': normalizar_data(pagamento['date_last_modified']),
                'marketplace_fee': pagamento['marketplace_fee'],
                'reference_id': normalizar_valor(pagamento['reference_id']),
                'authorization_code': pagamento['authorization_code']
            }

            # Adicionar dados de transferência ATM se existirem
            if 'atm_transfer_reference' in pagamento and pagamento['atm_transfer_reference'] != "None":
                pagamento_dict.update({
                    'atm_transaction_id': normalizar_valor(pagamento['atm_transfer_reference'].get('transaction_id')),
                    'atm_company_id': normalizar_valor(pagamento['atm_transfer_reference'].get('company_id'))
                })

            pagamentos.append(pagamento_dict)

            # Ações disponíveis para o pagamento
            if 'available_actions' in pagamento and pagamento['available_actions'] and pagamento[
                'available_actions'] != "None":
                for acao in pagamento['available_actions']:
                    if acao:  # Verificar se a ação não está vazia
                        acoes_disponiveis.append({
                            'pagamento_id': pagamento['id'],
                            'acao': acao
                        })

        tabelas['pagamentos'] = pd.DataFrame(pagamentos)
        if acoes_disponiveis:
            tabelas['acoes_pagamento'] = pd.DataFrame(acoes_disponiveis)

    # Tabela de feedback (se houver dados válidos)
    if dados['feedback'] and dados['feedback'] != "None":
        feedback_vendedor = dados['feedback']['seller']
        feedback_comprador = dados['feedback']['buyer']

        if (feedback_vendedor and feedback_vendedor != "None") or (feedback_comprador and feedback_comprador != "None"):
            feedback = {
                'pedido_id': dados['id'],
                'feedback_vendedor': json.dumps(
                    feedback_vendedor) if feedback_vendedor and feedback_vendedor != "None" else None,
                'feedback_comprador': json.dumps(
                    feedback_comprador) if feedback_comprador and feedback_comprador != "None" else None
            }
            tabelas['feedback'] = pd.DataFrame([feedback])

    # Tabela de order_request (pedidos de mudança/devolução)
    if dados['order_request'] and dados['order_request'] != "None":
        change_request = dados['order_request']['change']
        return_request = dados['order_request']['return']

        if (change_request and change_request != "None") or (return_request and return_request != "None"):
            requests = {
                'pedido_id': dados['id'],
                'change_request': json.dumps(change_request) if change_request and change_request != "None" else None,
                'return_request': json.dumps(return_request) if return_request and return_request != "None" else None
            }
            tabelas['order_requests'] = pd.DataFrame([requests])

    return tabelas


# Função para exportar tabelas para Excel
def exportar_para_excel(tabelas, nome_arquivo='../dados/pedidos_normalizados.xlsx'):
    """
    Exporta todas as tabelas para um arquivo Excel com múltiplas abas
    """
    with pd.ExcelWriter(nome_arquivo, engine='openpyxl') as writer:
        for nome_tabela, df in tabelas.items():
            if not df.empty:
                # Exporta o DataFrame para Excel
                df.to_excel(writer, sheet_name=nome_tabela, index=False)

                # Acessa a planilha para formatar
                worksheet = writer.sheets[nome_tabela]

                # Ajusta a largura de todas as colunas com base no conteúdo
                for idx, col in enumerate(df.columns):
                    # Determina a largura máxima na coluna
                    max_length = 0
                    column_letter = worksheet.cell(row=1, column=idx + 1).column_letter

                    # Verifica o comprimento do cabeçalho
                    max_length = max(max_length, len(str(col)))

                    # Verifica o comprimento de cada valor na coluna
                    for i in range(len(df)):
                        cell_value = str(df.iloc[i, idx])
                        max_length = max(max_length, len(cell_value))

                    # Adiciona um pequeno buffer
                    adjusted_width = (max_length + 2) * 1.2

                    # Define a largura da coluna
                    worksheet.column_dimensions[column_letter].width = adjusted_width

                # Encontra a posição da coluna 'pedido_id' se existir
                if 'pedido_id' in df.columns:
                    col_idx = df.columns.get_loc('pedido_id') + 1  # +1 porque openpyxl usa indexação baseada em 1

                    # Aplica formato numérico à coluna inteira
                    for row in range(2, len(df) + 2):  # Começa em 2 para pular o cabeçalho
                        cell = worksheet.cell(row=row, column=col_idx)
                        cell.number_format = '0'  # Formato numérico sem casas decimais

                if 'id' in df.columns:
                    col_idx = df.columns.get_loc('id') + 1  # +1 porque openpyxl usa indexação baseada em 1

                    # Aplica formato numérico à coluna inteira
                    for row in range(2, len(df) + 2):  # Começa em 2 para pular o cabeçalho
                        cell = worksheet.cell(row=row, column=col_idx)
                        cell.number_format = '0'  # Formato numérico sem casas decimais




    print(f"Arquivo '{nome_arquivo}' criado com sucesso com {len(tabelas)} abas.")


# Função para processar múltiplos pedidos
def processar_multiplos_pedidos(dados_lista):
    """
    Processa uma lista de pedidos e combina os resultados em tabelas consolidadas
    """
    todas_tabelas = {}

    # Processar cada pedido individualmente
    for dados in dados_lista:
        tabelas_pedido = processar_json_para_tabelas(dados)

        # Combinar as tabelas de todos os pedidos
        for nome_tabela, df in tabelas_pedido.items():
            if nome_tabela in todas_tabelas:
                # Concatenar com tabelas existentes
                if not df.empty:
                    if todas_tabelas[nome_tabela].empty:
                        todas_tabelas[nome_tabela] = df.copy()
                    else:
                        # Garantir que os tipos de dados sejam consistentes antes da concatenação
                        for col in df.columns:
                            if col in todas_tabelas[nome_tabela].columns:
                                # Converter para o mesmo tipo se possível
                                try:
                                    df[col] = df[col].astype(todas_tabelas[nome_tabela][col].dtype)
                                except:
                                    pass
                        todas_tabelas[nome_tabela] = pd.concat([todas_tabelas[nome_tabela], df], ignore_index=True)
            else:
                # Criar nova tabela
                todas_tabelas[nome_tabela] = df

    return todas_tabelas


# Função para verificar se todos os campos necessários existem
def validar_pedido(dados):
    """
    Valida se um pedido tem os campos necessários antes de processá-lo
    """
    campos_obrigatorios = ['id']

    for campo in campos_obrigatorios:
        if campo not in dados:
            return False

    return True


# Função para processar um arquivo JSON com múltiplos pedidos
def processar_arquivo_json(arquivo):
    """
    Processa um arquivo JSON que contém múltiplos pedidos
    """
    dados = carregar_json(arquivo_json=arquivo)

    # Verificar se o JSON é uma lista ou um objeto único
    if isinstance(dados, list):
        # Filtrar apenas dados válidos
        dados_validos = [pedido for pedido in dados if validar_pedido(pedido)]
        return processar_multiplos_pedidos(dados_validos)
    else:
        # É um único objeto
        if validar_pedido(dados):
            return processar_json_para_tabelas(dados)
        else:
            print("O objeto JSON não contém os campos necessários!")
            return {}


# Exemplo de uso
def main():
    # Você pode usar esta função para testar o código
    # Substitua por seu próprio JSON ou use um arquivo
    json_exemplo = '''
    [
      {
         "id":2000010268238790,
         "date_created":"2024-12-22T15:55:43.000-04:00"
      },
      {
         "id":2000010268238791,
         "date_created":"2024-12-23T10:30:22.000-04:00"
      }
    ]
    '''  # Seu JSON aqui

    # Processar o JSON (agora como uma lista de pedidos)
    # dados_lista = carregar_json(json_string=json_exemplo)
    arquivo_json = "../dados/pedidos.json"
    dados_lista = carregar_json(arquivo_json=arquivo_json)

    # Verificar se os dados são uma lista ou um único objeto
    if isinstance(dados_lista, list):
        tabelas = processar_multiplos_pedidos(dados_lista)
    else:
        tabelas = processar_json_para_tabelas(dados_lista)

    # Exportar para Excel
    exportar_para_excel(tabelas)

    # Exibir informações sobre as tabelas criadas
    print("Tabelas criadas:")
    for nome, df in tabelas.items():
        print(f"- {nome}: {len(df)} linhas, {len(df.columns)} colunas")





if __name__ == "__main__":
    main()