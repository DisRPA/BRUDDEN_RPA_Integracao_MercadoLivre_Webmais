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
            insert_values = tuple(row[col] if col in row else None for col in [
                "Nome NF", "Nota", "Valor", "Banco", "Frete/Taxa", "Mercado Pago",
                "Order_ID ML", "Tipo de Doc", "No. Doc", "Cod. Cliente WebMais",
                "No. Pedido WebMais", "OBS"
            ])
            cursor.execute(insert_query, insert_values)

            # Segundo: UPDATE para sobrescrever campos (exceto os de controle)
            update_query = f"""
            UPDATE {tabela}
            SET Valor=?, Banco=?, "Frete/Taxa"=?, "Mercado Pago"=?, "Order_ID ML"=?, 
                "Tipo de Doc"=?, "No. Doc"=?, "Cod. Cliente WebMais"=?, "No. Pedido WebMais"=?, OBS=?
            WHERE "Nome NF"=? AND Nota=?
            """
            update_values = tuple(row[col] if col in row else None for col in [
                "Valor", "Banco", "Frete/Taxa", "Mercado Pago", "Order_ID ML",
                "Tipo de Doc", "No. Doc", "Cod. Cliente WebMais",
                "No. Pedido WebMais", "OBS"
            ]) + (row["Nome NF"], row["Nota"])
            cursor.execute(update_query, update_values)

        conn.commit()
        logging.info(f"{len(dados)} registros inseridos/atualizados com sucesso!")
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

