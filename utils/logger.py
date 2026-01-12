import logging
import os
import sys
from pathlib import Path
from datetime import date
import glob


# Função chamada na primeira importação
def setup_logger(log_file_name="logfile.txt"):
    log_file = Path(__file__).parent.parent / "logs" / log_file_name

    # Cria diretório logs se não existir
    log_file.parent.mkdir(exist_ok=True)

    if not log_file.exists():
        log_file.touch()
        os.chmod(log_file, 0o777)

    # Configuração do logger
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),  # Salva em arquivo
            logging.StreamHandler(sys.stdout)         # Exibe no console
        ]
    )


def limpar_logs_por_data(quantidade_arquivos=12):
    # Obter a lista de arquivos no diretório (ajuste a extensão se necessário)
    diretorio_logs = Path(__file__).parent.parent / "logs"
    arquivos = glob.glob(os.path.join(diretorio_logs, "logfile_*.txt"))

    # Ordenar os arquivos pela data de modificação (do mais recente para o mais antigo)
    arquivos.sort(key=os.path.getmtime, reverse=True)

    # Manter apenas os 10 mais recentes e excluir os demais
    arquivos_para_excluir = arquivos[quantidade_arquivos:]  # Pegamos todos os arquivos além dos 10 mais recentes

    for arquivo in arquivos_para_excluir:
        os.remove(arquivo)
        logging.info(f"Arquivo de log removido: {arquivo}")


hoje = date.today().strftime("%Y-%m-%d")
setup_logger(f"logfile_{hoje}.txt")

