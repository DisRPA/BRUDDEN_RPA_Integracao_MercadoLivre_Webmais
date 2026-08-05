# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RPA (Robotic Process Automation) for Brudden that integrates **Mercado Livre** (marketplace) with **WebMais** (ERP system). The automation:

1. **Fetches sales data** from Mercado Livre API (orders, billing, shipping, client info)
2. **Consolidates** the data into structured reports (JSON/Excel)
3. **Performs invoice write-offs** (baixa de notas) in the WebMais ERP via browser automation (Playwright)

## Commands

Always activate the virtual environment before running anything:
```bash
source .venv/bin/activate
```

Run the main pipeline (from `src/` directory):
```bash
cd src && python consulta_mercado_livre.py   # passo=1 fetches ML data, passo=2 consolidates
cd src && python baixa_de_nfs.py             # reads Excel, writes to DB, performs ERP write-offs
```

For the Playwright-based ERP automation, Chrome must be launched first with remote debugging:
```bash
google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-playwright --no-first-run --no-default-browser-check --disable-features=MediaRouter,PrivacySandboxSettings4,Translate --disable-component-update --disable-sync https://erp2.webmaissistemas.com.br/csp/kelt/system/www/index.csp
```

Install dependencies (no requirements.txt exists; packages installed manually):
```bash
pip install requests pandas openpyxl python-dotenv numpy playwright
playwright install chromium
```

## Architecture

### Pipeline Flow

```
Mercado Livre API  -->  JSON files (dados/)  -->  Consolidated JSON  -->  Excel  -->  SQLite DB  -->  WebMais ERP (Playwright)
```

### Source Modules (`src/`)

- **`consulta_mercado_livre.py`** - Main orchestrator. Two-step process controlled by `passo` parameter:
  - `passo=1`: Calls ML API to fetch orders by period, saves `pedidos_{period}.json` and `dados_relatorio_{period}.json`
  - `passo=2`: Consolidates data, queries WebMais for client/NF codes, generates Excel
- **`baixa_de_nfs.py`** - Reads finalized Excel from `dados/lancamento/`, inserts into SQLite, then automates invoice write-offs in WebMais via Playwright
- **`gera_excel_pedidos.py`** - Parses raw ML order JSON into normalized relational DataFrames (pedidos, itens, pagamentos, etc.) and exports to multi-sheet Excel

### Utilities (`utils/`)

- **`api_mercado_livre.py`** - Production ML API client: orders, billing, shipping, client data. All calls use retry logic (3 attempts with 2s delay)
- **`api_mercadolivre_testes.py`** - Experimental/test ML API endpoints
- **`api_mercadolivre_reports.py`** - ML billing report generation/status endpoints
- **`ml_autenticacao.py`** - OAuth token management (get, refresh, auto-renew). Writes tokens to `.env`
- **`acesso_webmais.py`** - Playwright browser automation for WebMais ERP: login, client lookups, NF queries, invoice write-offs. Connects to Chrome via CDP (`localhost:9222`). The write-off function `lanca_baixa_de_valores` handles NFs split into multiple lines/títulos in the ERP — see "Baixa multi-linha" below
- **`tratamento_de_dados.py`** - Data transformation: creates DataFrames from ML billing data, consolidates orders by invoice/shipping, computes fees
- **`gera_excel.py`** - Converts consolidated JSON to formatted Excel (openpyxl)
- **`banco_de_dados.py`** - SQLite operations for `database/control.db`: CRUD for `vendas_mercado_livre` table
- **`dotenv_utils.py`** - Reads/writes `.env` file values programmatically
- **`logger.py`** - Logging setup: daily log files in `logs/`, auto-cleanup of old logs

### Baixa multi-linha (NF dividida em N títulos)

Implementado em `utils/acesso_webmais.py` (`lanca_baixa_de_valores`) em jun/2026. O WebMais às vezes divide uma mesma NF em **várias linhas/títulos** na tela "Liquidação por Filtro" (ex.: uma nota de R$101,00 vira 2 linhas de R$50,50). A versão antiga lia só a 1ª linha (`campo4`) e gerava falsa "Divergência no valor total" (valor no sistema = metade do total).

Como funciona agora:
- **`_detectar_parcelas(iframe)`** lê todas as `<tr class="itens">` do iframe `centro2` (atributos `data-pos`, `data-saldo`, e Doc. Or. em `cells[2].title`). O campo de baixa de cada linha é `campo{4*pos}` e o checkbox é `op{pos}`.
- **Validação**: a soma dos saldos das linhas tem que bater com a soma dos componentes pendentes (Banco + Mercado Pago + Frete/Taxa), tolerância `max(0.02, 0.01*n_linhas)`. Senão → `erro=1` com mensagem de divergência. Busca por NF tenta o campo `'6'` e, em fallback, o `'1'`.
- **Rateio por componente**: cada componente é baixado em sua conta (Banco→1, Mercado Pago→22, Frete/Taxa→5), rateado proporcionalmente ao saldo de cada linha via `_ratear_centavos` (método do maior resto, soma exata em centavos). O **último componente pendente absorve o saldo restante** de cada linha, garantindo fechamento exato. Entre componentes a página recarrega, então as linhas são redetectadas a cada passo.
- **Caso single-line**: comportamento idêntico ao anterior (1 linha → preenche o valor cheio de cada componente). Sem regressão.
- **Limitação conhecida**: NFs cujo saldo aparece como `0,00` na liquidação ("Nota X não encontrada no WebMais") são um problema distinto (nota não localizada), não multi-linha — seguem como `erro=1`.

Validado ao vivo em 18/06/2026 (NF 49492 e 49960). Mesmo padrão existe no projeto irmão `BRUDDEN_RPA_Integracao_Shopee`.

### Data Storage

- **`dados/`** - JSON data files (`pedidos_*.json`, `dados_relatorio_*.json`, consolidated JSONs) and generated Excel reports. Subdirectory `lancamento/` holds finalized Excel files for import
- **`database/control.db`** - SQLite DB tracking write-off status per invoice (campos `baixa_valor_nota`, `baixa_valor_mercado_pago`, `baixa_valor_frete`)
- **`.env`** - ML tokens (access/refresh), WebMais credentials. Tokens are auto-refreshed and written back

## Key Conventions

- Python 3.10, no requirements.txt or pyproject.toml - dependencies managed manually in `.venv`
- All source code and comments are in **Portuguese (pt-BR)**
- Scripts in `src/` use relative paths (`../dados/`) - must be run from `src/` directory
- ML API token refresh is automatic: checks expiration, subtracts 20min margin, refreshes via OAuth
- Playwright connects to an already-running Chrome instance via CDP, not a fresh browser launch
- The SQLite table `vendas_mercado_livre` uses composite unique key `(Nome NF, Nota)` with `ON CONFLICT REPLACE`
- Write-off process is incremental: tracks 3 independent flags per invoice (`baixa_valor_nota`, `baixa_valor_mercado_pago`, `baixa_valor_frete`)
