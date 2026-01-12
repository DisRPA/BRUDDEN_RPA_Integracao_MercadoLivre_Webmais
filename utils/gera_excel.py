import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter


# Carregar os dados do JSON
def converter_json_para_excel(arquivo_json_consolidado, arquivo_excel):
    # Ler o arquivo JSON
    df_consolidado = pd.read_json(arquivo_json_consolidado, orient='records')

    # df_consolidado.drop(columns=['Apelido', 'Frete Cliente', 'Status'], inplace=True)
    df_consolidado.drop(columns=['Apelido', 'Frete Cliente'], inplace=True)

    # Converter Order_ID ML para string para preservar os dígitos
    df_consolidado['Order_ID ML'] = df_consolidado['Order_ID ML'].astype(str)

    # for index, row in df_consolidado.iterrows():
    #     print(row["Nome NF"], row["Nota"], row["Valor"], row["Order_ID ML"])

    # Definir formatos para colunas com valores numéricos
    colunas_numericas = ['C', 'D', 'E', 'F']

    # Salvar os dados em um arquivo Excel
    df_consolidado.to_excel(arquivo_excel, index=False)

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
