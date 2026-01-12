from utils.dotenv_utils import set_env_value
from datetime import datetime, timedelta, UTC
import requests
import json
import time
import os
from dotenv import load_dotenv

# Configurações
CLIENT_ID = "612439810072537"  # FESO   612439810072537
CLIENT_SECRET = "d1MVjEmCnYdRW6eVB6OSWH5EFtaTuVGh"  # FESO  jBAPjPrFiVBJK0qERZKSE85P3NRNQvgb

REDIRECT_URI = "https://bubblebot.com.br/php/logger.php"
TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
API_TEST_URL = "https://api.mercadolibre.com/users/me"

# Consuta feso para gerar o token
# https://auth.mercadolivre.com.br/authorization?response_type=code&client_id=612439810072537&redirect_uri=https://bubblebot.com.br/php/logger.php

# Trocar o código de autorização pelo access_token
def get_access_token(auth_code):
    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": auth_code,
        "redirect_uri": REDIRECT_URI
    }
    response = requests.post(TOKEN_URL, data=data)
    response_data = response.json()


    if "access_token" in response_data:
        return {
            "access_token": response_data["access_token"],
            "refresh_token": response_data["refresh_token"],
            "expires_in": response_data["expires_in"]
        }
    else:
        raise Exception(f"Erro ao obter token: {response_data}")


# Testar chamadas autenticadas com o access_token
def test_authenticated_request(access_token):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(API_TEST_URL, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Erro na requisição autenticada: {response.text}")


# Renovar o token antes de expirar
def refresh_access_token(refresh_token):
    data = {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "read",
        "refresh_token": refresh_token
    }
    response = requests.post(TOKEN_URL, data=data)
    response_data = response.json()

    if "access_token" in response_data:
        return {
            "access_token": response_data["access_token"],
            "expires_in": response_data["expires_in"]
        }
    else:
        raise Exception(f"Erro ao renovar token: {response_data}")


def atualizar_token_com_refresh_token():
    load_dotenv()
    refresh_token = os.getenv("ML_REFRESH_TOKEN")
    new_token_data = refresh_access_token(refresh_token)
    new_access_token = new_token_data["access_token"]
    set_env_value("ML_ACCESSTOKEN", new_access_token)

    token_expiration = new_token_data["expires_in"]
    # Subtrai 20 minutos de margem (1200s)
    expiration_time = datetime.now(UTC) + timedelta(seconds=new_token_data["expires_in"] - 1200)
    expiration_str = expiration_time.isoformat()
    set_env_value("ML_ACCESSTOKEN_EXPIRATION", expiration_str)

# Exemplo de uso
if __name__ == "__main__":

    get_access_token("TG-68c1d0bc92779800016c7fda-276359269")

    expiration_str = os.getenv("ML_ACCESSTOKEN_EXPIRATION")
    if not expiration_str:
        atualizar_token_com_refresh_token()
        print("Token ML atualizado!!")
    else:
        expiration_dt = datetime.fromisoformat(expiration_str)
        if expiration_dt.tzinfo is None:
            expiration_dt = expiration_dt.replace(tzinfo=UTC)

        if datetime.now(UTC) > expiration_dt:
            atualizar_token_com_refresh_token()
            print("Token ML atualizado!!")

    ACCESS_TOKEN = os.getenv("ML_ACCESSTOKEN")

    # refresh_token = 'TG-67bf17acdf5dff0001d3789f-276359269'  # FESO
    # # auth_code = input("Cole aqui o código de autorização: ")
    # auth_code = 'TG-67bf17acdf5dff0001d3789f-276359269'
    # # Passo 4: Obter o token inicial
    # token_data = get_access_token(auth_code)
    # access_token = token_data["access_token"]
    # refresh_token = token_data["refresh_token"]
    # expires_in = token_data["expires_in"]
    #
    # print("Access Token obtido com sucesso!")
    # print(f"Token expira em {expires_in} segundos.")
    #
    # # Passo 5: Testar chamada autenticada
    # print("\nTestando requisição autenticada...")
    # user_data = test_authenticated_request(access_token)
    # print(json.dumps(user_data, indent=2, ensure_ascii=False))
    #
    # # Simulação de expiração do token e renovação (Passo 6)
    # print("\nAguardando expiração do token...")
    # time.sleep(5)  # Troque para expires_in - 10 para um teste real
    #
    # print("\nRenovando Access Token...")
    # refresh_token = 'TG-67c9e3e9e7a038000152fd66-11635294'
    # new_token_data = refresh_access_token(refresh_token)
    # new_access_token = new_token_data["access_token"]
    # print("Novo Access Token:", new_access_token)
