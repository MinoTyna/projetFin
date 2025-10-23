import requests

url = "http://127.0.0.1:8000/paiement/lancer/"
data = {
    "numero_client": "0343500001",
    "montant": 1000
}

response = requests.post(url, json=data)
print("Status code:", response.status_code)
print("Response:", response.text)
