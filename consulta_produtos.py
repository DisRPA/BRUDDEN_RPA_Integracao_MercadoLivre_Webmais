import requests
import json


def get_user_id(ACCESS_TOKEN):
    # URL para obter informações do usuário logado
    API_URL = "https://api.mercadolibre.com/users/me"

    # Headers com autenticação
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    # Fazer requisição para obter o User ID
    response = requests.get(API_URL, headers=headers)

    # Verificar se a requisição foi bem-sucedida
    if response.status_code == 200:
        user_data = response.json()
        user_id = user_data.get("id")
        print(f"Seu User ID no Mercado Livre é: {user_id}")
        return user_id
    else:
        print(f"Erro ao obter User ID: {response.text}")


def consulta_produtos(USER_ID, ACCESS_TOKEN):
    # URL para obter produtos ativos (à venda)
    API_URL = f"https://api.mercadolibre.com/users/{USER_ID}/items/search?status=active"

    # Headers com autenticação
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    # Fazer requisição para obter os produtos
    response = requests.get(API_URL, headers=headers)

    # Verificar se a requisição foi bem-sucedida
    if response.status_code == 200:
        data = response.json()
        item_ids = data.get("results", [])

        print(f"Produtos encontrados: {len(item_ids)}")

        # Caso tenha produtos, buscar detalhes dos produtos
        if item_ids:
            item_details_url = f"https://api.mercadolibre.com/items?ids={','.join(item_ids)}"
            details_response = requests.get(item_details_url, headers=headers)

            if details_response.status_code == 200:
                items = details_response.json()
                print(json.dumps(items, indent=2, ensure_ascii=False))
            else:
                print(f"Erro ao obter detalhes dos produtos: {details_response.text}")
        else:
            print("Nenhum produto encontrado.")

    else:
        print(f"Erro ao buscar produtos: {response.text}")



if __name__ == "__main__":
    # Configurações (substitua pelos seus valores)
    ACCESS_TOKEN = "APP_USR-473383081016493-022514-0052fda101e2d9b018882005326875d7-11635294"
    USER_ID = get_user_id(ACCESS_TOKEN)  # Você pode obter esse ID com /users/me
    print(USER_ID)
    consulta_produtos(USER_ID, ACCESS_TOKEN)