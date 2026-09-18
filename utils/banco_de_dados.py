from utils.logger import logging
import os
import sqlite3
from datetime import date, datetime
import pandas as pd


# Registrar adaptadores e conversores
def registrar_adaptadores():
    def adapt_date(val):
        return val.isoformat()

    def adapt_datetime(val):
        return val.isoformat()

    def convert_date(val):
        return date.fromisoformat(val.decode())

    def convert_datetime(val):
        return datetime.fromisoformat(val.decode())

    # Registrar os adaptadores e conversores
    sqlite3.register_adapter(date, adapt_date)
    sqlite3.register_adapter(datetime, adapt_datetime)
    sqlite3.register_converter("DATE", convert_date)
    sqlite3.register_converter("DATETIME", convert_datetime)


# Configurar a conexão com o banco
def criar_conexao():
    # Database Path
    diretorio_atual = os.path.dirname(os.path.abspath(__file__))
    database_path = os.path.abspath(os.path.join(diretorio_atual, "..", "database", "control.db"))

    registrar_adaptadores()  # Certifique-se de registrar antes da conexão
    return sqlite3.connect(database_path, detect_types=sqlite3.PARSE_DECLTYPES)


def criar_tabela_vendas_mercado_livre():
    """
    Cria a tabela 'vendas_mercado_livre' no banco de dados SQLite.
    Se já existir, não será recriada.
    """
    conn = None
    try:
        conn = criar_conexao()
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendas_mercado_livre (
            id INTEGER PRIMARY KEY,
            'Nome NF' TEXT NOT NULL,
            Nota TEXT NOT NULL,
            Valor REAL,
            Banco REAL,
            'Frete/Taxa' REAL,
            'Mercado Pago' REAL,
            'Order_ID ML' TEXT,
            'Tipo de Doc' TEXT,
            'No. Doc' TEXT,
            'Cod. Cliente WebMais' TEXT,
            'No. Pedido WebMais' TEXT,
            OBS TEXT,
            baixa_valor_nota INTEGER DEFAULT (0) NOT NULL,
            baixa_valor_mercado_pago INTEGER DEFAULT (0) NOT NULL,
            baixa_valor_frete INTEGER DEFAULT (0) NOT NULL,
            erro INTEGER DEFAULT (0) NOT NULL,
            descricao_erro TEXT,
            UNIQUE('Nome NF', Nota, 'Order_ID ML') ON CONFLICT REPLACE
        )
        """)

        # Adicionar colunas erro e descricao_erro caso a tabela já exista sem elas
        try:
            cursor.execute("ALTER TABLE vendas_mercado_livre ADD COLUMN erro INTEGER DEFAULT (0) NOT NULL")
        except sqlite3.OperationalError:
            pass  # Coluna já existe
        try:
            cursor.execute("ALTER TABLE vendas_mercado_livre ADD COLUMN descricao_erro TEXT")
        except sqlite3.OperationalError:
            pass  # Coluna já existe

        conn.commit()
        # logging.info("Tabela 'vendas_mercado_livre' criada com sucesso!")

    except sqlite3.Error as e:
        logging.error(f"Erro ao criar a tabela: {e}")

    finally:
        if conn:
            conn.close()


def inserir_na_tabela(dados: pd.DataFrame, tabela="vendas_mercado_livre"):
    """Insere os dados do DataFrame na tabela"""
    conn = criar_conexao()
    try:
        dados.to_sql(tabela, conn, if_exists="append", index=False)
        logging.info(f"{len(dados)} registros inseridos com sucesso!")
    except Exception as e:
        logging.error(f"Erro ao inserir dados: {e}")
        raise


# Chave única da tabela (ver UNIQUE em criar_tabela_vendas_mercado_livre) e colunas
# de valor conferidas após a gravação.
COLUNAS_CHAVE_UNICA = ["Nome NF", "Nota", "Order_ID ML"]
COLUNAS_VALOR_CONFERENCIA = ["Valor", "Banco", "Frete/Taxa", "Mercado Pago"]


def _valor_para_bind(valor):
    """Converte NaN/NaT em None para o bind ficar idêntico no INSERT e na conferência."""
    if valor is None:
        return None
    try:
        if pd.isna(valor):
            return None
    except (TypeError, ValueError):
        pass
    return valor


def _total_da_coluna(dados, coluna):
    if coluna not in dados.columns:
        return 0.0
    return round(float(pd.to_numeric(dados[coluna], errors="coerce").fillna(0).sum()), 2)


def conferir_gravacao(cursor, dados, tabela):
    """Confere se o que ficou no banco é igual ao que veio no DataFrame.

    Compara pela chave única (Nome NF, Nota, Order_ID ML) a quantidade de linhas de
    cada chave, o total de linhas e os totais das colunas de valor. Devolve a lista
    de divergências encontradas (lista vazia = gravação fiel ao arquivo).
    """
    divergencias = []

    linhas_por_chave = {}
    for _, row in dados.iterrows():
        chave = tuple(
            _valor_para_bind(row[col]) if col in row else None
            for col in COLUNAS_CHAVE_UNICA
        )
        linhas_por_chave[chave] = linhas_por_chave.get(chave, 0) + 1

    where = " AND ".join(f'"{col}" IS ?' for col in COLUNAS_CHAVE_UNICA)
    somas_sql = ", ".join(f'COALESCE(SUM("{col}"), 0)' for col in COLUNAS_VALOR_CONFERENCIA)

    linhas_no_banco = 0
    totais_no_banco = {col: 0.0 for col in COLUNAS_VALOR_CONFERENCIA}

    for chave, qtd_no_arquivo in linhas_por_chave.items():
        cursor.execute(f"SELECT COUNT(*), {somas_sql} FROM {tabela} WHERE {where}", chave)
        resultado = cursor.fetchone()
        qtd_no_banco = resultado[0]
        linhas_no_banco += qtd_no_banco
        for coluna, soma in zip(COLUNAS_VALOR_CONFERENCIA, resultado[1:]):
            totais_no_banco[coluna] += float(soma or 0)

        if qtd_no_banco != qtd_no_arquivo:
            nome_nf, nota, order_id = chave
            divergencias.append(
                f"- Nome NF={nome_nf}; Nota={nota}; Order_ID ML={order_id}: "
                f"{qtd_no_arquivo} linha(s) no arquivo e {qtd_no_banco} no banco"
            )

    if linhas_no_banco != len(dados):
        divergencias.append(
            f"- Quantidade de linhas: {len(dados)} no arquivo e {linhas_no_banco} no banco"
        )

    for coluna in COLUNAS_VALOR_CONFERENCIA:
        total_arquivo = _total_da_coluna(dados, coluna)
        total_banco = round(totais_no_banco[coluna], 2)
        if abs(total_arquivo - total_banco) > 0.005:
            divergencias.append(
                f'- Total de "{coluna}": {total_arquivo:.2f} no arquivo e '
                f"{total_banco:.2f} no banco (diferença de {total_arquivo - total_banco:+.2f})"
            )

    return divergencias


def inserir_ou_atualizar_vendas(dados: pd.DataFrame, tabela="vendas_mercado_livre"):
    conn = criar_conexao()
    cursor = conn.cursor()

    try:
        for _, row in dados.iterrows():
            # Primeiro: INSERT OR IGNORE
            insert_query = f"""
            INSERT OR IGNORE INTO {tabela} 
            ("Nome NF", Nota, Valor, Banco, "Frete/Taxa", "Mercado Pago", "Order_ID ML", 
             "Tipo de Doc", "No. Doc", "Cod. Cliente WebMais", "No. Pedido WebMais", OBS)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            insert_values = tuple(_valor_para_bind(row[col]) if col in row else None for col in [
                "Nome NF", "Nota", "Valor", "Banco", "Frete/Taxa", "Mercado Pago",
                "Order_ID ML", "Tipo de Doc", "No. Doc", "Cod. Cliente WebMais",
                "No. Pedido WebMais", "OBS"
            ])
            cursor.execute(insert_query, insert_values)

            # Segundo: UPDATE para sobrescrever campos (exceto os de controle).
            # O WHERE tem que usar a chave única inteira. Filtrando só por Nome NF +
            # Nota, o UPDATE atingia todas as linhas da mesma nota e reescrevia o
            # "Order_ID ML" delas com o mesmo valor; as linhas ficavam iguais na chave
            # única e o ON CONFLICT REPLACE apagava uma sem log e sem erro.
            update_query = f"""
            UPDATE {tabela}
            SET Valor=?, Banco=?, "Frete/Taxa"=?, "Mercado Pago"=?, 
                "Tipo de Doc"=?, "No. Doc"=?, "Cod. Cliente WebMais"=?, "No. Pedido WebMais"=?, OBS=?
            WHERE "Nome NF" IS ? AND Nota IS ? AND "Order_ID ML" IS ?
            """
            update_values = tuple(_valor_para_bind(row[col]) if col in row else None for col in [
                "Valor", "Banco", "Frete/Taxa", "Mercado Pago",
                "Tipo de Doc", "No. Doc", "Cod. Cliente WebMais",
                "No. Pedido WebMais", "OBS"
            ]) + tuple(
                _valor_para_bind(row[col]) if col in row else None
                for col in COLUNAS_CHAVE_UNICA
            )
            cursor.execute(update_query, update_values)

        # Confere antes do commit: se o banco não ficou igual ao arquivo, desfaz tudo.
        divergencias = conferir_gravacao(cursor, dados, tabela)
        if divergencias:
            conn.rollback()
            mensagem = (
                "A gravação no banco não ficou igual ao arquivo e foi DESFEITA "
                "(nenhum registro foi gravado).\n"
                "Corrija o arquivo antes de executar novamente.\n"
                + "\n".join(divergencias)
            )
            logging.error(mensagem)
            raise ValueError(mensagem)

        conn.commit()
        totais = "; ".join(
            f"{coluna}={_total_da_coluna(dados, coluna):.2f}"
            for coluna in COLUNAS_VALOR_CONFERENCIA
        )
        logging.info(
            f"{len(dados)} registros gravados e conferidos com o arquivo "
            f"(totais: {totais})."
        )
    except ValueError:
        raise
    except Exception as e:
        conn.rollback()
        logging.error(f"Erro ao inserir/atualizar dados: {e}")
        raise
    finally:
        conn.close()


def atualizar_tabela_com_df_campos_existentes(df, tabela="vendas_mercado_livre"):
    conn = None
    try:
        conn = criar_conexao()
        cursor = conn.cursor()

        # Obtem os nomes das colunas da tabela no banco
        cursor.execute(f"PRAGMA table_info({tabela})")
        colunas_tabela = [info[1] for info in cursor.fetchall()]

        for _, row in df.iterrows():
            # Usa apenas colunas que estão no df, que não são 'id' e que existem na tabela
            colunas = [col for col in df.columns if col != 'id' and col in colunas_tabela and pd.notna(row[col])]
            if not colunas:
                continue

            set_clause = ", ".join([f"'{col}' = ?" for col in colunas])
            query = f"""
            UPDATE {tabela}
            SET {set_clause}
            WHERE id = ?
            """
            valores = tuple(row[col] for col in colunas) + (row['id'],)
            cursor.execute(query, valores)

        conn.commit()

    except sqlite3.Error as e:
        logging.error(f"Erro ao atualizar registros: {e}")

    finally:
        if conn:
            conn.close()


def consulta_tabela(tabela):
    conn = criar_conexao()
    try:
        query = f"SELECT * FROM {tabela}"
        df = pd.read_sql_query(query, conn)
        # logging.info(f"Dados lidos da tabela '{tabela}'!")
        return df
    finally:
        conn.close()


def consulta_tabela_filtro_mes(tabela,  mes: int):
    conn = criar_conexao()
    try:
        query = f"SELECT * FROM {tabela} WHERE mes = ?"
        df = pd.read_sql_query(query, conn, params=[mes])  # Passando o mes como lista
        # Ou alternativamente:
        # df = pd.read_sql_query(query, conn, params={'mes': mes})  # Usando dicionário
        logging.info(f"Dados lidos da tabela '{tabela}' para o cod {mes}!")
        return df
    finally:
        conn.close()


def consulta_tabela_com_filtro(tabela: str, nome_campo: str, valor):
    conn = criar_conexao()
    try:
        if not tabela.isidentifier() or not nome_campo.isidentifier():
            raise ValueError("Nome da tabela ou coluna inválido")

        query = f"SELECT * FROM {tabela} WHERE {nome_campo} = ?"
        df = pd.read_sql_query(query, conn, params=[valor])
        logging.info(f"Dados lidos da tabela '{tabela}' para o campo '{nome_campo}' com valor '{valor}'!")
        return df
    finally:
        conn.close()


def apagar_tabela_com_filtro(tabela: str, nome_campo: str, valor):
    conn = criar_conexao()
    try:
        if not tabela.isidentifier() or not nome_campo.isidentifier():
            raise ValueError("Nome da tabela ou coluna inválido")

        query = f"DELETE FROM {tabela} WHERE {nome_campo} = ?"
        cursor = conn.cursor()
        cursor.execute(query, (valor,))
        conn.commit()

        # Verifica se alguma linha foi afetada
        if cursor.rowcount == 0:
            logging.warning(
                f"Nenhum registro encontrado na tabela '{tabela}' para '{nome_campo}' = '{valor}'. Nenhuma exclusão realizada.")
        else:
            logging.info(
                f"{cursor.rowcount} registros da tabela '{tabela}' onde '{nome_campo}' = '{valor}' foram apagados com sucesso!")
    finally:
        conn.close()


def atualizar_registro_numero_pedido(dados, tabela: str, numero_pedido: str):
    conn = criar_conexao()
    try:
        # Garantindo que 'dados' seja um DataFrame
        if isinstance(dados, pd.Series):
            dados = dados.to_frame().T  # Converte para DataFrame de uma única linha

        elif isinstance(dados, dict):
            dados = pd.DataFrame([dados])  # Converte dicionário para DataFrame

        elif not isinstance(dados, pd.DataFrame):
            raise TypeError("O parâmetro 'dados' deve ser um DataFrame, Series ou dicionário.")

        # Convertendo o DataFrame para um dicionário de registros
        dados_dict = dados.to_dict(orient='records')[0]

        # Criando a query de UPDATE dinamicamente
        set_clause = ", ".join([f"{col} = ?" for col in dados_dict.keys()])
        query = f"""
        UPDATE {tabela} 
        SET {set_clause} 
        WHERE numero_pedido = ?
        """

        # Executando a atualização
        cursor = conn.cursor()
        cursor.execute(query, list(dados_dict.values()) + [numero_pedido])

        conn.commit()
    finally:
        conn.close()



def inserir_apenas_campos_do_df(tabela, dados: pd.DataFrame):
    """
    Insere ou atualiza dados na tabela especificada.
    Se o numero_pedido não existir, insere a linha.
    Se o numero_pedido existir, atualiza apenas os campos presentes no DataFrame.
    """
    conn = criar_conexao()
    try:
        cursor = conn.cursor()
        registros_inseridos = 0
        registros_atualizados = 0

        # Obter metadados da tabela
        colunas_info = pd.read_sql(f"PRAGMA table_info({tabela})", conn)
        colunas_tabela = colunas_info['name'].tolist()

        # Filtrar apenas colunas válidas (que existem na tabela)
        colunas_validas = [col for col in dados.columns if col in colunas_tabela]

        # Para cada linha no DataFrame
        for _, row in dados.iterrows():
            # Verificar se este número de pedido já existe
            numero_pedido = row['numero_pedido']
            cursor.execute(f"SELECT 1 FROM {tabela} WHERE numero_pedido = ?", (numero_pedido,))
            existe = cursor.fetchone()

            if not existe:
                # Inserção - o número de pedido não existe
                colunas = ", ".join(colunas_validas)
                placeholders = ", ".join(["?"] * len(colunas_validas))
                valores = [row[col] for col in colunas_validas]

                cursor.execute(f"INSERT INTO {tabela} ({colunas}) VALUES ({placeholders})", valores)
                registros_inseridos += 1
            else:
                # Atualização - o número de pedido já existe
                # Atualiza apenas os campos presentes no DataFrame
                set_clause = ", ".join([f"{col} = ?" for col in colunas_validas if col != 'numero_pedido'])
                if set_clause:  # Verifica se há campos para atualizar além do numero_pedido
                    valores = [row[col] for col in colunas_validas if col != 'numero_pedido']
                    valores.append(numero_pedido)  # Para a cláusula WHERE

                    cursor.execute(f"UPDATE {tabela} SET {set_clause} WHERE numero_pedido = ?", valores)
                    registros_atualizados += 1

        conn.commit()
        logging.info(
            f"{registros_inseridos} registros inseridos e {registros_atualizados} registros atualizados com sucesso!")
        return registros_inseridos, registros_atualizados

    except Exception as e:
        conn.rollback()
        logging.error(f"Erro ao inserir/atualizar dados: {e}")
        raise


# criar_tabela_vendas_mercado_livre()



# ---------------------------------------------------------------------------
# Relatórios enviados ao cliente
#
# O relatório do ML repete pedidos de meses anteriores e o cliente apaga linhas
# na conferência (canceladas que não geraram nota, por exemplo). Não dá para
# filtrar por Status: há pedido "cancelled" no ML cuja nota existe e foi paga
# (ex.: NF 50731 de jul/2026). A única fonte confiável do que o cliente quis
# fora é a comparação entre o que foi ENVIADO e o que ele DEVOLVEU revisado.
# ---------------------------------------------------------------------------

TABELA_RELATORIOS = "relatorios_enviados"


def criar_tabela_relatorios_enviados():
    conn = criar_conexao()
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABELA_RELATORIOS} (
            id INTEGER PRIMARY KEY,
            periodo TEXT NOT NULL,
            'Order_ID ML' TEXT NOT NULL,
            'Nome NF' TEXT,
            Nota TEXT,
            Valor REAL,
            Banco REAL,
            'Frete/Taxa' REAL,
            'Mercado Pago' REAL,
            Status TEXT,
            enviado_em TEXT NOT NULL,
            removido_pelo_cliente INTEGER DEFAULT (0) NOT NULL,
            conferido_em TEXT,
            UNIQUE(periodo, 'Order_ID ML') ON CONFLICT REPLACE
        )
        """)
        conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Erro ao criar a tabela {TABELA_RELATORIOS}: {e}")
        raise
    finally:
        conn.close()


def registrar_relatorio_enviado(dados: pd.DataFrame, periodo: str):
    """Guarda a foto do relatório gerado para o cliente conferir."""
    criar_tabela_relatorios_enviados()
    conn = criar_conexao()
    try:
        cursor = conn.cursor()
        agora = datetime.now().isoformat(timespec="seconds")
        for _, row in dados.iterrows():
            cursor.execute(f"""
            INSERT INTO {TABELA_RELATORIOS}
            (periodo, "Order_ID ML", "Nome NF", Nota, Valor, Banco, "Frete/Taxa",
             "Mercado Pago", Status, enviado_em, removido_pelo_cliente, conferido_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL)
            """, (
                periodo,
                str(row.get("Order_ID ML")),
                row.get("Nome NF"),
                str(row.get("Nota")),
                _valor_para_bind(row.get("Valor")),
                _valor_para_bind(row.get("Banco")),
                _valor_para_bind(row.get("Frete/Taxa")),
                _valor_para_bind(row.get("Mercado Pago")),
                row.get("Status"),
                agora,
            ))
        conn.commit()
        logging.info(
            f"Relatório do período {periodo} registrado: {len(dados)} linha(s) enviadas ao cliente."
        )
    except sqlite3.Error as e:
        conn.rollback()
        logging.error(f"Erro ao registrar o relatório enviado: {e}")
        raise
    finally:
        conn.close()


def registrar_conferencia_do_cliente(periodo: str, order_ids_devolvidos):
    """Marca o que o cliente tirou do relatório na revisão.

    Compara o que foi enviado com o que voltou no Excel de dados/lancamento/.
    Devolve o DataFrame das linhas removidas. Se o período não foi registrado
    (relatório gerado antes desta função existir), devolve None.
    """
    criar_tabela_relatorios_enviados()
    conn = criar_conexao()
    try:
        enviados = pd.read_sql(
            f"SELECT * FROM {TABELA_RELATORIOS} WHERE periodo = ?", conn, params=(periodo,)
        )
        if enviados.empty:
            logging.warning(
                f"Período {periodo} não tem relatório registrado no banco. "
                "Não dá para saber o que o cliente removeu nesta revisão."
            )
            return None

        devolvidos = {str(order_id) for order_id in order_ids_devolvidos}
        removidos = enviados[~enviados["Order_ID ML"].astype(str).isin(devolvidos)]

        cursor = conn.cursor()
        agora = datetime.now().isoformat(timespec="seconds")
        cursor.execute(
            f"UPDATE {TABELA_RELATORIOS} SET removido_pelo_cliente = 0, conferido_em = ? "
            "WHERE periodo = ?",
            (agora, periodo),
        )
        for order_id in removidos["Order_ID ML"].astype(str):
            cursor.execute(
                f"UPDATE {TABELA_RELATORIOS} SET removido_pelo_cliente = 1, conferido_em = ? "
                'WHERE periodo = ? AND "Order_ID ML" IS ?',
                (agora, periodo, order_id),
            )
        conn.commit()
        return removidos
    except sqlite3.Error as e:
        conn.rollback()
        logging.error(f"Erro ao registrar a conferência do cliente: {e}")
        raise
    finally:
        conn.close()


def consulta_removidos_pelo_cliente():
    """Order_ID ML -> período em que o cliente removeu a linha do relatório."""
    criar_tabela_relatorios_enviados()
    conn = criar_conexao()
    try:
        df = pd.read_sql(
            f'SELECT "Order_ID ML" AS order_id, periodo FROM {TABELA_RELATORIOS} '
            "WHERE removido_pelo_cliente = 1",
            conn,
        )
        return dict(zip(df["order_id"].astype(str), df["periodo"]))
    finally:
        conn.close()
