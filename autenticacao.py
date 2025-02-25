import requests
import json
import time

# Configurações
CLIENT_ID = "473383081016493"
CLIENT_SECRET = "rvM5T5wrpPybaZGdZXZXnpeVNB2HeH45"
REDIRECT_URI = "https://bubblebot.com.br/php/logger.php"
TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
API_TEST_URL = "https://api.mercadolibre.com/users/me"


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
        "refresh_token": refresh_token
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
        raise Exception(f"Erro ao renovar token: {response_data}")


# Exemplo de uso
if __name__ == "__main__":
    # auth_code = input("Cole aqui o código de autorização: ")
    auth_code = 'TG-67be0c47aef7fe000196fc3d-11635294'
    # Passo 4: Obter o token inicial
    token_data = get_access_token(auth_code)
    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]
    expires_in = token_data["expires_in"]

    print("Access Token obtido com sucesso!")
    print(f"Token expira em {expires_in} segundos.")

    # Passo 5: Testar chamada autenticada
    print("\nTestando requisição autenticada...")
    user_data = test_authenticated_request(access_token)
    print(json.dumps(user_data, indent=2, ensure_ascii=False))

    # Simulação de expiração do token e renovação (Passo 6)
    print("\nAguardando expiração do token...")
    time.sleep(5)  # Troque para expires_in - 10 para um teste real

    print("\nRenovando Access Token...")
    new_token_data = refresh_access_token(refresh_token)
    new_access_token = new_token_data["access_token"]
    print("Novo Access Token:", new_access_token)
