from utils.logger import logging
from utils.banco_de_dados import atualizar_tabela_com_df_campos_existentes
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from datetime import datetime, timedelta
from time import sleep
import pandas as pd
import json
import os


def fecha_popup_caso_exista(page):
    try:
        # novo popup
        page.click('button[title="Close"]', timeout=10000)
    except Exception as e:
        pass

    return page


def aguardar_pag_carregar_sem_networkidle(page):
    page.wait_for_timeout(300)
    page.wait_for_load_state('domcontentloaded')
    page.wait_for_load_state('load')

    # max_tentativas = 3
    # for _ in range(max_tentativas):
    #     try:
    #         page.wait_for_load_state('networkidle', timeout=1000)
    #         return page
    #     except:
    #         # Espera um pouco e tenta novamente
    #         page.wait_for_timeout(1000)

    return page


def aguardar_pag_carregar(page):
    page.wait_for_timeout(1000)
    page.wait_for_load_state('domcontentloaded')
    page.wait_for_load_state('load')

    max_tentativas = 3
    for _ in range(max_tentativas):
        try:
            page.wait_for_load_state('networkidle', timeout=1000)
            return page
        except:
            # Espera um pouco e tenta novamente
            page.wait_for_timeout(1000)

    return page


def login_webmais(page):
    page.wait_for_selector('#UserName', state="visible")
    page.fill('#UserName', os.getenv('WEBMAIS_USER'))
    page.wait_for_selector('#Password', state="visible")
    page.fill('#Password', os.getenv('WEBMAIS_PASS'))
    page.wait_for_selector('#botaoLogin', state="visible")
    page.click('#botaoLogin')
    page = aguardar_pag_carregar(page)

    page = fecha_popup_caso_exista(page)

    page = aguardar_pag_carregar(page)

    return page


def selecionar_nota(page, no_nota, segunda_tentativa=False):
    campo = '6'
    if segunda_tentativa:
        campo = '1'
    page.select_option('select#op', value=campo)

    page.fill('#txtTexto', "")
    page.fill('#txtTexto', no_nota)
    page.click('#btnPesquisa')
    page = aguardar_pag_carregar_sem_networkidle(page)
    sleep(3)
    return page, segunda_tentativa


def lanca_baixa_de_valores(page, row, data_do_saque_mercado_livre, segunda_tentativa=False):

    # Selecionar nota
    no_nota = row["Nota"]
    page, segunda_tentativa = selecionar_nota(page, no_nota, segunda_tentativa=segunda_tentativa)

    iframe = page.frame("centro2")  # Seleciona o iframe pelo id

    # Valida o valor da nota
    try:
        valor_atual = iframe.input_value('input[name="campo4"]', timeout=1000).replace('.','')
    except:
        valor_atual = '0,00'

    valor_total_nota = round(float(row["Valor"]), 2)
    if row["baixa_valor_nota"] == 1:
        valor_total_nota -= round(float(row["Banco"]), 2)
    if row["baixa_valor_mercado_pago"] == 1:
        valor_total_nota -= round(float(row["Mercado Pago"]), 2)
    if row["baixa_valor_frete"] == 1:
        valor_total_nota -= round(float(row["Frete/Taxa"]), 2)
    valor_pendente = f"{abs(valor_total_nota):.2f}".replace(".", ",")

    if valor_atual != valor_pendente and not segunda_tentativa:
        segunda_tentativa = True
        page, row = lanca_baixa_de_valores(page, row, data_do_saque_mercado_livre, segunda_tentativa=segunda_tentativa)
    elif valor_atual != valor_pendente:
        logging.error(f"Divergência no valor total da nota {no_nota} - Pendente {valor_pendente} - valor no sistema {valor_atual}")
        return page, row


    numero_conta_bradesco = "1"  # Conta do valor "BANCO"
    numero_conta_despesa_frete_e_taxa = "5"   # Conta do valor "Frete/Taxa"
    numero_conta_despesa_mercado_pago = "22"  # Conta do valor "Mercado Pago"

    page.fill('#txtDataBaseCom', "")
    page.fill('#txtDataBaseCom', data_do_saque_mercado_livre)

    # Se não foi dado baixa do valor nota
    # valor_banco = f"{row["Banco"]:.2f}".replace(".", ",")
    valor_banco = f"{row["Banco"]:.2f}".replace(".", ",")
    if row['baixa_valor_nota'] == 0 and valor_banco != '0,00':
        # Banco BRADESCO Feso  para o valor a receber
        page.fill('#txtConta2', "")
        page.fill('#txtConta2', numero_conta_bradesco)
        page.press("#txtConta2", "Enter")

        # iframe.eval_on_selector('input[name="campo4"]', 'el => { el.value = ""; }')
        iframe.fill('input[name="campo4"]', "")
        iframe.fill('input[name="campo4"]', valor_banco)

        iframe.click('input#op1')

        page.click('#btnBaixa')
        page = aguardar_pag_carregar_sem_networkidle(page)
        sleep(1)
        row['baixa_valor_nota'] = 1

        df_row = pd.DataFrame([row])
        atualizar_tabela_com_df_campos_existentes(df_row)

    page.fill('#txtDataBaseCom', "")
    page.fill('#txtDataBaseCom', data_do_saque_mercado_livre)

    # Se não foi dado baixa do valor do Mercado Livre
    valor_mercado_pago = f"{row["Mercado Pago"]:.2f}".replace(".", ",")
    if valor_mercado_pago == '0,00':
        row['baixa_valor_mercado_pago'] = 1

    if row['baixa_valor_mercado_pago'] == 0 and valor_mercado_pago != '0,00':
        # Banco BRADESCO Feso  para o valor a receber
        page.fill('#txtConta2', "")
        page.fill('#txtConta2', numero_conta_despesa_mercado_pago)
        page.press("#txtConta2", "Enter")

        # iframe.eval_on_selector('input[name="campo4"]', 'el => { el.value = ""; }')
        iframe.fill('input[name="campo4"]', "")
        iframe.fill('input[name="campo4"]', valor_mercado_pago)

        iframe.click('input#op1')

        page.click('#btnBaixa')
        page = aguardar_pag_carregar_sem_networkidle(page)
        sleep(1)
        row['baixa_valor_mercado_pago'] = 1

        df_row = pd.DataFrame([row])
        atualizar_tabela_com_df_campos_existentes(df_row)


    page.fill('#txtDataBaseCom', "")
    page.fill('#txtDataBaseCom', data_do_saque_mercado_livre)

    # Se não foi dado baixa do valor do Frete
    valor_frete_e_taxa = f"{row["Frete/Taxa"]:.2f}".replace(".", ",")
    if valor_frete_e_taxa == '0,00':
        row['baixa_valor_frete'] = 1

    if row['baixa_valor_frete'] == 0 and valor_frete_e_taxa != '0,00':
        # Banco BRADESCO Feso  para o valor a receber
        page.fill('#txtConta2', "")
        page.fill('#txtConta2', numero_conta_despesa_frete_e_taxa)
        page.press("#txtConta2", "Enter")

        # iframe.eval_on_selector('input[name="campo4"]', 'el => { el.value = ""; }')
        iframe.fill('input[name="campo4"]', "")
        iframe.fill('input[name="campo4"]', valor_frete_e_taxa)

        iframe.click('input#op1')

        page.click('#btnBaixa')
        page = aguardar_pag_carregar_sem_networkidle(page)
        sleep(1)

        row['baixa_valor_frete'] = 1

        df_row = pd.DataFrame([row])
        atualizar_tabela_com_df_campos_existentes(df_row)


    df_row = pd.DataFrame([row])
    atualizar_tabela_com_df_campos_existentes(df_row)
    return page, row


def navega_para_baixa_de_valores(page, data_do_saque_mercado_livre):
    page.click("i.mdi-currency-usd")
    sleep(1)
    page.click("#tituloSubNivel6XX70XX0")
    sleep(1)
    page.click("#tituloSubNivel6XX79XX70")
    sleep(1)
    page.click("#tituloSubNivel6XX82XX79")
    with page.expect_popup() as popup_info:
        page.click('a[title="Liquidação por Filtro"]')

    new_page = popup_info.value
    page.close()
    page = new_page
    # new_page = page.context.pages[-1]

    page = aguardar_pag_carregar(page)

    page = fecha_popup_caso_exista(page)

    page.fill('#txtDataBaixa', "")
    page.fill('#txtDataBaixa', data_do_saque_mercado_livre)
    page.fill('#dataCredito', "")
    page.fill('#dataCredito', data_do_saque_mercado_livre)
    page.fill('#txtDataBaseCom', "")
    page.fill('#txtDataBaseCom', data_do_saque_mercado_livre)
    page.fill('#txtDataBaseJurosMulta', "")
    page.fill('#txtDataBaseJurosMulta', data_do_saque_mercado_livre)

    return page


def navega_para_consulta_de_clientes(page):
    page.click("i.mdi-file-plus-outline")
    page.click("#tituloSubNivel11XX153XX0")
    # page.click("#tituloSubNivel6XX79XX70")
    # page.click("#tituloSubNivel6XX82XX79")
    with page.expect_popup() as popup_info:
        page.click('a[title="Clientes"]')

    new_page = popup_info.value
    page.close()
    page = new_page
    # new_page = page.context.pages[-1]

    page = aguardar_pag_carregar(page)

    page = fecha_popup_caso_exista(page)

    return page


def navega_para_liquidacao_por_filtro(page):
    page.click("i.mdi-currency-usd")
    page.click("#tituloSubNivel6XX70XX0")
    page.click("#tituloSubNivel6XX79XX70")
    page.click("#tituloSubNivel6XX82XX79")
    with page.expect_popup() as popup_info:
        page.click('a[title="Consulta Nota Fiscal"]')

    new_page = popup_info.value
    page.close()
    page = new_page
    # new_page = page.context.pages[-1]

    page = aguardar_pag_carregar(page)

    page = fecha_popup_caso_exista(page)

    return page


def navega_para_consulta_de_notas(page):
    page.click("i.mdi-store-outline")
    page.click("#tituloSubNivel8XX115XX0")
    page.click("#tituloSubNivel8XX192XX115")
    # page.click("#tituloSubNivel6XX82XX79")
    with page.expect_popup() as popup_info:
        page.click('a[title="Consulta Nota Fiscal"]')

    new_page = popup_info.value
    page.close()
    page = new_page
    # new_page = page.context.pages[-1]

    page = aguardar_pag_carregar(page)

    page = fecha_popup_caso_exista(page)

    return page


def abre_site_webmais_e_login(page):
    load_dotenv()

    # browser = p.chromium.launch(channel="chromium", headless=headless)
    # # browser.new_context(java_script_enabled=True)
    # context = browser.new_context(
    #     user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edg/114.0.1823.55 Safari/537.36",
    #     viewport={'width': 1530, 'height': 860},
    #     java_script_enabled=True,
    #     bypass_csp=True,  # bypass Content Security Policy
    #     ignore_https_errors=True,
    #     extra_http_headers={'Accept-Language': 'pt-BR,pt;q=0.9'}
    # )
    #
    # page = context.new_page()
    #
    # # Faz login no WebMais
    # page.goto("https://erp2.webmaissistemas.com.br/csp/kelt/system/www/index.csp")
    # page = aguardar_pag_carregar(page)

    page = login_webmais(page)

    return page


def consulta_cod_cliente(page, no_doc):
    page.fill('#pscnpjcpf', "")
    page.fill('#pscnpjcpf', no_doc)
    page.press("#pscnpjcpf", "Enter")
    sleep(0.3)
    page.click('#btnPesquisar')
    sleep(0.3)
    page = aguardar_pag_carregar(page)

    cod_cliente = page.locator("div#content td").first.text_content().strip()

    return page, cod_cliente


def consulta_nummero_nf_cliente(page, cod_cliente, valor_nf, data_ini, invoice_number):
    page.fill('#datainicio', "")
    page.fill('#datainicio', data_ini)
    page.fill('#cliente2', "")
    page.fill('#cliente2', cod_cliente)
    page.press("#cliente2", "Enter")
    sleep(0.3)

    page.click('#btnPesquisar')
    sleep(0.3)
    page = aguardar_pag_carregar(page)

    # Localiza a primeira linha da tabela dentro de #content que atende aos critérios
    rows = page.locator("div#content table.list tbody tr.trList")

    nota = nr_pedido = None
    for i in range(rows.count()):
        row = rows.nth(i)

        tipo_op = row.locator("td:nth-child(6)").inner_text().strip()
        status_nfe = row.locator("td:nth-child(8)").inner_text().strip()
        nfe_webmais = int(row.locator("td:nth-child(2)").inner_text().strip())

        print(f"Invoice_number: {invoice_number}  -  Cod Cliente {cod_cliente}")
        if type(invoice_number) == int and invoice_number != 0:
            if nfe_webmais == invoice_number:
                nota = invoice_number
                nota_webmais = row.locator("td:nth-child(2)").inner_text().strip()
                nr_pedido = row.locator("td:nth-child(9)").inner_text().strip()
                valor_total = row.locator("td:nth-child(10)").inner_text().strip()

                # Converte valor para float (troca vírgula por ponto)
                valor_total_float = float(valor_total.replace(".", "").replace(",", "."))

                if valor_nf == valor_total_float:
                    print(f"Invoice: {invoice_number} Nota: {nota_webmais}, Nr. Pedido: {nr_pedido}, Valor Total: {valor_total_float}, Cod Cliente {cod_cliente}")
                    break
                else:
                    print(f"ERRO NO VALOR@@@@@@@@@@@@@@@@@@@@@  Invoice: {invoice_number} Nota: {nota_webmais} == , Nr. Pedido: {nr_pedido}, Valor Total: {valor_total_float}, Cod Cliente {cod_cliente}")
        else:
            if tipo_op == "VENDA NORMAL" and status_nfe == "Autorizada":
                nota = row.locator("td:nth-child(2)").inner_text().strip()
                nr_pedido = row.locator("td:nth-child(9)").inner_text().strip()
                valor_total = row.locator("td:nth-child(10)").inner_text().strip()

                # Converte valor para float (troca vírgula por ponto)
                valor_total_float = float(valor_total.replace(".", "").replace(",", "."))

                if valor_nf == valor_total_float:
                    print(f"Nota: {nota}, Nr. Pedido: {nr_pedido}, Valor Total: {valor_total_float}, Cod Cliente {cod_cliente}")
                    break
                else:
                    print(f"ERRO NO VALOR@@@@@@@@@@@@@@@@@@@@@  Nota: {nota}, Nr. Pedido: {nr_pedido}, Valor Total: {valor_total_float}, Cod Cliente {cod_cliente}")


    return page, nota, nr_pedido


def consulta_numero_nf_por_doc_cliente(arquivo_json):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # headless = True
    # if "gugab" in current_dir or "gustavo" in current_dir:
    #     headless = False

    # Ler o arquivo JSON
    with open(arquivo_json, 'r', encoding='utf-8') as f:
        dados = json.load(f)

    dados_para_consulta = sum(
        1 for item in dados
        if item.get('No. Doc') not in [None, '', '-']
    )

    if dados_para_consulta == 0:
        print("Sem registros para consulta de nota fiscal")
        return

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]  # contexto persistente do perfil aberto
        page = context.pages[0]

        page = abre_site_webmais_e_login(page)

        page = navega_para_consulta_de_clientes(page)

        for item in dados:
            if item.get('No. Doc') is not None and item.get('Cod. Cliente WebMais', None) is None:
                no_doc = item.get('No. Doc')
                page, cod_cliente = consulta_cod_cliente(page, no_doc)
                item['Cod. Cliente WebMais'] = str(cod_cliente)

        # Atualiza o arquivo Json
        with open(arquivo_json, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=4)

        page = navega_para_consulta_de_notas(page)

        # data inicial da consulta
        data_ini = (datetime.today() - timedelta(days=60)).strftime('%d/%m/%Y')

        for item in dados:
            # if item["Apelido"] == "GABRIEL ANDRADE_P":
            #     print(f"Cliente {item["Apelido"]}")
            if item.get('Cod. Cliente WebMais') is not None and item.get('No. Pedido WebMais', None) is None:
                cod_cliente = item['Cod. Cliente WebMais']
                valor_nf = item['Valor']
                invoice_number = item['Nota']
                page, nota, nr_pedido = consulta_nummero_nf_cliente(page, cod_cliente, valor_nf, data_ini, invoice_number)
                if nota:
                    item['Nota'] = int(nota)

                if nr_pedido:
                    item['No. Pedido WebMais'] = int(nr_pedido)

        # Atualiza o arquivo Json
        with open(arquivo_json, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=4)

    print("fim")


def realiza_baixa_de_notas(df_notas, data_do_saque_mercado_livre, login):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # headless = True
    # if "gugab" in current_dir or "gustavo" in current_dir:
    #     headless = False

    headless = True
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]  # contexto persistente do perfil aberto
        page = context.pages[0]

        if login:
            page = abre_site_webmais_e_login(page)

        page = navega_para_baixa_de_valores(page, data_do_saque_mercado_livre)

        # Confirma qualquer botão de confirmação do navegador.
        page.on('dialog', lambda dialog: dialog.accept())

        total = len(df_notas)
        for i, (index, row) in enumerate(df_notas.iterrows(), start=1):
        # for index, row in df_notas.iloc[:4].iterrows():

            if row['baixa_valor_nota'] == row['baixa_valor_mercado_pago'] == row['baixa_valor_frete'] == 1:
                logging.info(f"{i} de {total} - NF {row['Nota']} já baixada anteriormente.")
                continue

            page, row = lanca_baixa_de_valores(page, row, data_do_saque_mercado_livre)
            logging.info(f"{i} de {total} - Baixa realizada para a nf {row['Nota']}.")