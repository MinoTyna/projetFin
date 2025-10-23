import requests
import uuid
from datetime import datetime
from django.conf import settings
from .models import PaiementMobile

def initier_paiement_sandbox(paiement: PaiementMobile):
    """Envoie le paiement au sandbox MVola"""
    url = "https://pre-api.mvola.mg/mvola/mm/transactions/type/merchantpay/1.0.0/"

    headers = {
        "Authorization": f"Bearer {settings.MVOLA_SANDBOX_TOKEN}",
        "Version": "1.0",
        "X-CorrelationID": str(uuid.uuid4()),
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Callback-URL": f"{settings.SITE_URL}/paiements/callback/",
    }

    transaction_ref = f"TXN-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    paiement.transaction_reference = transaction_ref
    paiement.save()

    data = {
        "amount": str(int(paiement.montant)),
        "currency": "MGA",
        "descriptionText": "Paiement test achat en ligne",
        "requestingOrganisationTransactionReference": transaction_ref,
        "requestDate": datetime.now().isoformat(),
        "debitParty": [{"key": "msisdn", "value": paiement.numero_client}],
        "creditParty": [{"key": "msisdn", "value": paiement.numero_entreprise}],
        "metadata": [
            {"key": "partnerName", "value": "MVola Sandbox Test"},
            {"key": "purpose", "value": "Paiement test"}
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        res_json = response.json()

        if response.status_code in [200, 202]:
            return f"✅ Paiement sandbox initié, transaction_ref: {transaction_ref}"
        else:
            paiement.statut = 'echoue'
            paiement.save()
            return f"❌ Échec sandbox: {res_json.get('errorDescription', 'Erreur inconnue')}"

    except Exception as e:
        paiement.statut = 'echoue'
        paiement.save()
        return f"❌ Exception lors du paiement sandbox: {str(e)}"
