import requests
import json

def generate_report(ACCESS_TOKEN):
    url = "https://api.mercadolibre.com/billing/integration/periods/key/2025-02-01/reports"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "group": "ML",
        "document_type": "BILL",
        "report_format": "XLSX"
    }

    response = requests.post(url, json=data, headers=headers)

    return response.json()


def get_report_status(ACCESS_TOKEN, report_id):
    url = f"https://api.mercadolibre.com/billing/integration/reports/{report_id}/status?document_type=BILL"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers)

    return response.json()


