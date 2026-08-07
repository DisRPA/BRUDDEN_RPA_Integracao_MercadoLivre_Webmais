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


def _detectar_parcelas(iframe):
    """Lê as linhas (títulos) listadas no iframe de liquidação por filtro.

    Uma NF pode ter sido dividida pelo WebMais em várias linhas/títulos da mesma
    nota (ex.: uma nota de R$101,00 aparece como 2 linhas de R$50,50). Retorna uma
    lista de dicts {id, pos (int), saldo (float), doc_or (str)} — uma por linha.
    O campo de baixa de cada linha é campo{4*pos} e o checkbox é op{pos}.
    """
    try:
        dados = iframe.eval_on_selector_all(
            'tr.itens',
            """rows => rows.map(tr => {
                const cells = tr.querySelectorAll('td');
                const docCell = cells[2];
                return {
                    id: tr.getAttribute('data-id'),
                    pos: tr.getAttribute('data-pos'),
                    saldo: tr.getAttribute('data-saldo'),
                    doc_or: docCell ? (docCell.getAttribute('title') || docCell.textContent).trim() : ''
                };
            })""",
        )
    except Exception as e:
        logging.warning(f"Falha ao detectar linhas da nota no WebMais: {e}")
        return []

    parcelas = []
    for d in dados:
        try:
            parcelas.append({
                'id': d['id'],
                'pos': int(d['pos']),
                'saldo': float(d['saldo']),
                'doc_or': (d['doc_or'] or '').strip(),
            })
        except (TypeError, ValueError):
            continue
    return parcelas


def _ratear_centavos(total_cent, pesos_cent):
    """Rateia total_cent (int, em centavos) proporcionalmente a pesos_cent (lista de int).

    Garante soma exata: distribui a sobra de centavos somando 1 centavo às linhas
    de maior resto fracionário (o "1 a mais numa linha, 1 a menos noutra").
    """
    n = len(pesos_cent)
    soma = sum(pesos_cent)
    if n == 0 or soma <= 0:
        return [0] * n
    exatos = [total_cent * p / soma for p in pesos_cent]
    base = [int(e) for e in exatos]
    resto = int(total_cent - sum(base))
    ordem = sorted(range(n), key=lambda i: exatos[i] - base[i], reverse=True)
    for k in range(resto):
        base[ordem[k % n]] += 1
    return base


def lanca_baixa_de_valores(page, row, data_do_saque_mercado_livre):

    no_nota = row["Nota"]

    numero_conta_bradesco = "1"  # Conta do valor "BANCO"  "24"
    numero_conta_despesa_frete_e_taxa = "5"   # Conta do valor "Frete/Taxa"
    numero_conta_despesa_mercado_pago = "22"  # Conta do valor "Mercado Pago"

    def _valor(coluna):
        v = row[coluna]
        return round(float(v), 2) if pd.notna(v) else 0.0

    # Componentes da nota, na ordem de baixa (coluna do valor, conta, flag de baixa).
    componentes_def = [
        ("Banco", numero_conta_bradesco, "baixa_valor_nota"),
        ("Mercado Pago", numero_conta_despesa_mercado_pago, "baixa_valor_mercado_pago"),
        ("Frete/Taxa", numero_conta_despesa_frete_e_taxa, "baixa_valor_frete"),
    ]

    # Componente de valor 0,00 não gera lançamento: marca como já baixado.
    for coluna_valor, _, flag_col in componentes_def:
        if _valor(coluna_valor) == 0:
            row[flag_col] = 1

    # Componentes ainda pendentes (flag 0 e valor != 0).
    componentes = [
        (coluna_valor, conta, flag_col, _valor(coluna_valor))
        for (coluna_valor, conta, flag_col) in componentes_def
        if row[flag_col] == 0
    ]
    if not componentes:
        atualizar_tabela_com_df_campos_existentes(pd.DataFrame([row]))
        return page, row

    total_componentes = round(sum(v for *_, v in componentes), 2)

    # Seleciona a nota e detecta as linhas (títulos). A NF pode ter sido dividida em
    # N linhas no WebMais; cada linha tem seu próprio campo de baixa (campo{4*pos}).
    # Tenta o campo de busca '6' e, em fallback, o '1' (igual ao fluxo single-line).
    parcelas = []
    melhor = None  # (parcelas, total_saldos) da melhor tentativa, para a mensagem de erro
    for segunda_tentativa in (False, True):
        page, _ = selecionar_nota(page, no_nota, segunda_tentativa=segunda_tentativa)
        iframe = page.frame("centro2")
        encontradas = _detectar_parcelas(iframe)
        if not encontradas:
            continue
        total_saldos = round(sum(p['saldo'] for p in encontradas), 2)
        tolerancia = max(0.02, 0.01 * len(encontradas))
        melhor = (encontradas, total_saldos)
        if abs(total_saldos - total_componentes) <= tolerancia:
            parcelas = encontradas
            break

    if not parcelas:
        if melhor is None:
            descricao = f"Nota {no_nota} não encontrada no WebMais."
        else:
            enc, total_saldos = melhor
            descricao = (f"Divergência no valor total da nota {no_nota} - "
                         f"Pendente {total_componentes:.2f} - saldo no sistema {total_saldos:.2f} "
                         f"em {len(enc)} linha(s)").replace(".", ",")
        logging.error(descricao)
        row['erro'] = 1
        row['descricao_erro'] = descricao
        atualizar_tabela_com_df_campos_existentes(pd.DataFrame([row]))
        return page, row

    # Todas as linhas têm que pertencer ao mesmo Doc. Or. (mesma nota); senão é ambíguo.
    docs = {p['doc_or'] for p in parcelas if p['doc_or']}
    if len(docs) > 1:
        descricao = f"Nota {no_nota}: linhas de Doc. Or. diferentes {docs}; baixa não automática."
        logging.error(descricao)
        row['erro'] = 1
        row['descricao_erro'] = descricao
        atualizar_tabela_com_df_campos_existentes(pd.DataFrame([row]))
        return page, row

    if len(parcelas) > 1:
        logging.info(f"Nota {no_nota}: dividida em {len(parcelas)} linhas no WebMais (Doc. Or. {docs}).")

    # Chegou aqui: tentativa válida. Limpa erro de tentativas anteriores.
    row['erro'] = 0
    row['descricao_erro'] = None

    # Baixa cada componente pendente. Entre baixas a página recarrega e os saldos das
    # linhas mudam, então as linhas são redetectadas a cada componente. O último
    # componente absorve o saldo restante de cada linha (fechamento exato em centavos).
    for k, (coluna_valor, conta, flag_col, valor) in enumerate(componentes):
        iframe = page.frame("centro2")
        parcelas_atuais = _detectar_parcelas(iframe)
        if not parcelas_atuais:
            descricao = f"Nota {no_nota}: linhas sumiram antes de baixar {coluna_valor}."
            logging.error(descricao)
            row['erro'] = 1
            row['descricao_erro'] = descricao
            atualizar_tabela_com_df_campos_existentes(pd.DataFrame([row]))
            return page, row

        saldos_cent = [round(p['saldo'] * 100) for p in parcelas_atuais]
        ultimo = (k == len(componentes) - 1)
        if ultimo:
            # Último componente: absorve todo o saldo restante de cada linha.
            valores_cent = saldos_cent
        else:
            valores_cent = _ratear_centavos(round(valor * 100), saldos_cent)

        if len(parcelas_atuais) > 1:
            logging.info(f"Nota {no_nota}: {coluna_valor} rateado por linha (centavos): {valores_cent}")

        page.fill('#txtDataBaseCom', "")
        page.fill('#txtDataBaseCom', data_do_saque_mercado_livre)

        page.fill('#txtConta2', "")
        page.fill('#txtConta2', conta)
        page.press("#txtConta2", "Enter")

        for parcela, v_cent in zip(parcelas_atuais, valores_cent):
            valor_str = f"{v_cent / 100:.2f}".replace(".", ",")
            campo = f'input[name="campo{4 * parcela["pos"]}"]'
            iframe.fill(campo, "")
            iframe.fill(campo, valor_str)
            iframe.click(f'input#op{parcela["pos"]}')

        page.click('#btnBaixa')
        page = aguardar_pag_carregar_sem_networkidle(page)
        sleep(1)

        row[flag_col] = 1
        atualizar_tabela_com_df_campos_existentes(pd.DataFrame([row]))

    atualizar_tabela_com_df_campos_existentes(pd.DataFrame([row]))
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
    page.fill('#cnpjCpf', "")
    page.fill('#cnpjCpf', no_doc)
    page.press("#cnpjCpf", "Enter")
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


def realiza_baixa_de_notas(df_notas, data_do_saque_mercado_livre):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # headless = True
    # if "gugab" in current_dir or "gustavo" in current_dir:
    #     headless = False

    headless = True
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]  # contexto persistente do perfil aberto
        page = context.pages[0]

        page_url = page.url
        if '/www/index.csp' in page_url:
            logging.info("inicia abre site webmais e login")
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
            if row.get('erro', 0) == 1:
                logging.warning(f"{i} de {total} - Baixa NÃO realizada para a nf {row['Nota']}: {row.get('descricao_erro', '')}")
            else:
                logging.info(f"{i} de {total} - Baixa realizada para a nf {row['Nota']}.")

        page.close()
        context.close()
        browser.close()