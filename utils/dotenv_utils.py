import os
from dotenv import load_dotenv
from pathlib import Path


def set_env_value(key, value, env_file_name=".env"):
    # Carrega o .env existente
    ROOT_DIR = Path(__file__).resolve().parent.parent
    env_file = os.path.join(ROOT_DIR, env_file_name)
    load_dotenv(dotenv_path=env_file)
    lines = []
    found = False

    with open(env_file, "r") as f:
        for line in f:
            if line.startswith(f"{key}="):
                lines.append(f"{key}={value}\n")
                found = True
            else:
                lines.append(line)

    if not found:
        lines.append(f"{key}={value}\n")

    with open(env_file, "w") as f:
        f.writelines(lines)

    # Recarrega as variáveis no ambiente
    load_dotenv(dotenv_path=env_file, override=True)
