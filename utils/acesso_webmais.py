from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import os

def aguardar_pag_carregar(page):
    page.wait_for_timeout(500)
    page.wait_for_load_state('domcontentloaded')  # espera DOM
    page.wait_for_load_state('load')  # espera carregamento completo
    page.wait_for_load_state('networkidle')  # espera rede ficar inativa
    return page


def login_webmais(page):
    page.wait_for_selector('#UserName', state="visible")
    page.fill('#UserName', os.getenv('WEBMAIS_USER'))
    page.wait_for_selector('#Password', state="visible")
    page.fill('#Password', os.getenv('WEBMAIS_PASS'))
    page.wait_for_selector('#botaoLogin', state="visible")
    page.click('#botaoLogin')
    page = aguardar_pag_carregar(page)
    return page


def baixa_de_valores(page, dados, numero_conta):
    # Selecionar nota
    page.select_option('select#op', value='6')

    page.fill('#txtTexto', "")
    page.fill('#txtTexto', dados["numero_nf"])
    page.click('#btnPesquisa')
    page = aguardar_pag_carregar(page)

    iframe = page.frame("centro2")  # Seleciona o iframe pelo id

    # Banco BRADESCO Feso  para o valor a receber
    page.fill('#txtConta2', numero_conta)
    page.press("#txtConta2", "Enter")

    valor_atual = iframe.input_value('input[name="campo4"]')
    if valor_atual == dados["valor_total"]:
        # iframe.eval_on_selector('input[name="campo4"]', 'el => { el.value = ""; }')
        iframe.fill('input[name="campo4"]', "")
        iframe.fill('input[name="campo4"]', dados["valor_baixa"])

        iframe.click('input#op1')

        # page.click('#btnBaixa')


def main(headless):
    load_dotenv()

    # Caminho relativo para o arquivo de destino
    current_dir = os.path.dirname(os.path.abspath(__file__))

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chromium", headless=headless)
        # browser.new_context(java_script_enabled=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edg/114.0.1823.55 Safari/537.36",
            viewport={'width': 1530, 'height': 860},
            java_script_enabled=True,
            bypass_csp=True,  # bypass Content Security Policy
            ignore_https_errors=True,
            extra_http_headers={'Accept-Language': 'pt-BR,pt;q=0.9'}
        )

        page = context.new_page()

        # Faz login no WebMais
        page.goto("https://erp2.webmaissistemas.com.br/csp/kelt/system/www/index.csp")
        page = aguardar_pag_carregar(page)

        page = login_webmais(page)

        page.click("i.mdi-currency-usd")
        page.click("#tituloSubNivel6XX70XX0")
        page.click("#tituloSubNivel6XX79XX70")
        page.click("#tituloSubNivel6XX82XX79")
        with page.expect_popup() as popup_info:
            page.click('a[title="Liquidação por Filtro"]')

        new_page = popup_info.value
        page.close()
        page = new_page
        # new_page = page.context.pages[-1]

        page = aguardar_pag_carregar(page)

        dados = {
            "numero_nf": "41234",
            "valor_total": "199,90",
            "valor_baixa": "139,97",
            "numero_conta_corrente": "1"
        }

        numero_conta = '1' # Bradesco Valores Mercado Livre

        baixa_de_valores(page, dados, numero_conta)







        # Confirma qualquer botão de confirmação do navegador.
        # page.on('dialog', lambda dialog: dialog.accept())
        print("fim")


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    headless = True
    if "gugab" in current_dir or "gustavo" in current_dir:
        headless = False
    main(headless)
