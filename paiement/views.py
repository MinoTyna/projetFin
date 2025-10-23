from decimal import Decimal
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Paiement, Achat
from dateutil.relativedelta import relativedelta
from responsable.models import Responsable
from .serializers import PaiementSerializer
from django.core.mail import EmailMessage
from .models import Paiement
from client.models import Client
from datetime import datetime, date, timedelta
from achats.models import Facture
from django.db.models import Max
from django.utils.timezone import now
from collections import defaultdict



def envoyer_sms(numero, message):
    # Simule l’envoi de SMS
    print(f"SMS envoyé à {numero} : {message}")


def envoyer_email(sujet, message, destinataires, reply_to=None):
    if not isinstance(destinataires, list):
        destinataires = [destinataires]

    email = EmailMessage(
        subject=sujet,
        body=message,
        from_email=None,  # utilisera DEFAULT_FROM_EMAIL de settings.py
        to=destinataires,
        reply_to=[reply_to] if reply_to else None
    )
    email.send(fail_silently=False)


from decimal import Decimal
from datetime import datetime
from dateutil.relativedelta import relativedelta
from rest_framework import generics, status
from rest_framework.response import Response
from .models import Paiement, Achat, Facture
from .serializers import PaiementSerializer
from django.db.models import Sum
# from .utils import envoyer_sms  # adapte selon ton projet


class PaiementCreateView(generics.CreateAPIView):
    queryset = Paiement.objects.all()
    serializer_class = PaiementSerializer

    def create(self, request, *args, **kwargs):
        client_id = request.data.get('client')
        if not client_id:
            return Response({"error": "Le champ 'client' est requis."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            montant_paye = Decimal(request.data.get('Paiement_montant', '0'))
        except:
            return Response({"error": "Le montant payé est invalide."}, status=status.HTTP_400_BAD_REQUEST)

        if montant_paye < Decimal('0'):
            return Response({"error": "Le montant minimum à payer est de 100 000 Ariary."},
                            status=status.HTTP_400_BAD_REQUEST)

        type_paiement = request.data.get('Paiement_type', '').lower()
        if type_paiement not in ['comptant', 'mensuel']:
            return Response({"error": "Type de paiement invalide."}, status=status.HTTP_400_BAD_REQUEST)

        montant_choisi = None
        date_choisie = None
        prochaine_date = None

        # 🔹 Gestion paiement mensuel
        if type_paiement == 'mensuel':
            dernier_paiement = Paiement.objects.filter(
                AchatsID__ClientID_id=client_id,
                Paiement_type='mensuel',
                Paiement_montantchoisi__isnull=False,
                Paiement_datechoisi__isnull=False
            ).order_by('-Paiement_date').first()

            if dernier_paiement:
                montant_choisi = dernier_paiement.Paiement_montantchoisi
                date_choisie = dernier_paiement.Paiement_datechoisi
                mois_a_ajouter = int(montant_paye / montant_choisi)
                prochaine_date = date_choisie + relativedelta(months=mois_a_ajouter)
            else:
                montant_choisi_str = request.data.get('Paiement_montantchoisi')
                date_choisie_str = request.data.get('Paiement_datechoisi')

                if not montant_choisi_str or not date_choisie_str:
                    return Response({
                        "error": "Le montant choisi et la date choisie sont requis pour le premier paiement mensuel."
                    }, status=status.HTTP_400_BAD_REQUEST)

                try:
                    montant_choisi = Decimal(montant_choisi_str)
                    date_choisie = datetime.strptime(date_choisie_str, "%Y-%m-%d").date()
                except:
                    return Response({"error": "Montant ou date invalide (format attendu : YYYY-MM-DD)."},
                                    status=status.HTTP_400_BAD_REQUEST)
                prochaine_date = date_choisie

        # 🔹 Vérifie les achats du client
        achats_client = Achat.objects.filter(ClientID_id=client_id)
        if not achats_client.exists():
            return Response({"error": "Aucun achat trouvé pour ce client."}, status=status.HTTP_404_NOT_FOUND)

        total_attendu = sum(achat.ProduitID.Produit_prix * achat.Achat_quantite for achat in achats_client)
        total_deja_paye = Paiement.objects.filter(AchatsID__ClientID_id=client_id).aggregate(
            total=Sum('Paiement_montant')
        )['total'] or Decimal('0')

        nouveau_total = total_deja_paye + montant_paye
        reste = max(total_attendu - nouveau_total, Decimal('0'))
        statut = "complet" if nouveau_total >= total_attendu else "incomplet"
        montant_rendu = int(nouveau_total - total_attendu) if nouveau_total > total_attendu else 0
        revenu = int(nouveau_total - total_attendu) if nouveau_total > total_attendu else 0

        dernier_achat = achats_client.order_by('-Achat_date').first()

        # 🔹 Génération numéro de facture
        last_facture = Facture.objects.order_by('-id').first()
        last_num = 0
        if last_facture and last_facture.numero_facture:
            import re
            match = re.search(r'FACT-(\d+)', last_facture.numero_facture)
            if match:
                last_num = int(match.group(1))
        new_num = last_num + 1
        numero_facture = f"FACT-{new_num:04d}"

        facture = Facture.objects.create(achat=dernier_achat, numero_facture=numero_facture)

        # 🔹 Création du paiement
        data = request.data.copy()
        data['AchatsID'] = dernier_achat.id
        data['Paiement_montant'] = montant_paye

        if type_paiement == 'mensuel':
            data['Paiement_montantchoisi'] = montant_choisi
            data['Paiement_datechoisi'] = prochaine_date
        else:
            data.pop('Paiement_montantchoisi', None)
            data.pop('Paiement_datechoisi', None)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        paiement = serializer.save()

        # 🔹 🔥 Test sandbox MVola (simulation mobile)
        if paiement.Paiement_mode in ['mvola', 'airtel', 'orange']:
            message_sandbox = paiement.verifier_paiement_mobile()
        else:
            message_sandbox = "Paiement classique enregistré avec succès."

        # 🔹 Envoi SMS
        client = dernier_achat.ClientID
        numero = client.Client_telephone
        envoyer_sms(numero, f"Bonjour {client.Client_nom}, votre paiement de {montant_paye:.0f} Ar a été reçu. "
                            f"Statut: {statut}. Reste à payer: {reste:.0f} Ar.")

        # 🔹 Préparation de la réponse
        produits_achetes = [
            {
                "nom": achat.ProduitID.Produit_nom,
                "quantite": achat.Achat_quantite,
                "prix_unitaire": int(achat.ProduitID.Produit_prix),
                "total": int(achat.ProduitID.Produit_prix * achat.Achat_quantite)
            }
            for achat in achats_client
        ]

        prixtotalproduit = sum(p["total"] for p in produits_achetes)
        nombredemois_restant = int(reste / montant_choisi) if montant_choisi else None

        return Response({
            "message_sandbox": message_sandbox,
            "repaiement": True if type_paiement == 'mensuel' and total_deja_paye > 0 else False,
            "client": client.Client_nom,
            "client_id": client.id,
            "produits": produits_achetes,
            "prixtotalproduit": prixtotalproduit,
            "total_paye": int(nouveau_total),
            "reste_a_payer": int(reste),
            "montant_rendu": montant_rendu,
            "revenu": revenu,
            "statut": statut,
            "Paiement_type": type_paiement,
            "Paiement_montantchoisi": int(montant_choisi) if montant_choisi else None,
            "nombredemois_restant": nombredemois_restant,
            "date_paiement_prochaine": str(prochaine_date) if prochaine_date else None,
            "numero_facture": facture.numero_facture,
            "facture_id": facture.id,
            "transaction_reference": paiement.transaction_reference,
            "statut_mobile": paiement.statut
        }, status=status.HTTP_201_CREATED)



# class PaiementCreateView(generics.CreateAPIView):
#     queryset = Paiement.objects.all()
#     serializer_class = PaiementSerializer

#     def create(self, request, *args, **kwargs):
#         client_id = request.data.get('client')
#         if not client_id:
#             return Response({"error": "Le champ 'client' est requis."}, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             montant_paye = Decimal(request.data.get('Paiement_montant', '0'))
#         except:
#             return Response({"error": "Le montant payé est invalide."}, status=status.HTTP_400_BAD_REQUEST)

#         if montant_paye < Decimal('0'):
#             return Response({"error": "Le montant minimum à payer est de 100 000 Ariary."}, status=status.HTTP_400_BAD_REQUEST)

#         type_paiement = request.data.get('Paiement_type', '').lower()
#         if type_paiement not in ['comptant', 'mensuel']:
#             return Response({"error": "Type de paiement invalide."}, status=status.HTTP_400_BAD_REQUEST)

#         montant_choisi = None
#         date_choisie = None
#         prochaine_date = None

#         if type_paiement == 'mensuel':
#             dernier_paiement = Paiement.objects.filter(
#                 AchatsID__ClientID_id=client_id,
#                 Paiement_type='mensuel',
#                 Paiement_montantchoisi__isnull=False,
#                 Paiement_datechoisi__isnull=False
#             ).order_by('-Paiement_date').first()

#             if dernier_paiement:
#                 montant_choisi = dernier_paiement.Paiement_montantchoisi
#                 date_choisie = dernier_paiement.Paiement_datechoisi
#                 mois_a_ajouter = int(montant_paye / montant_choisi)
#                 prochaine_date = date_choisie + relativedelta(months=mois_a_ajouter)
#             else:
#                 montant_choisi_str = request.data.get('Paiement_montantchoisi')
#                 date_choisie_str = request.data.get('Paiement_datechoisi')

#                 if not montant_choisi_str or not date_choisie_str:
#                     return Response({
#                         "error": "Le montant choisi et la date choisie sont requis pour le premier paiement mensuel."
#                     }, status=status.HTTP_400_BAD_REQUEST)

#                 try:
#                     montant_choisi = Decimal(montant_choisi_str)
#                     date_choisie = datetime.strptime(date_choisie_str, "%Y-%m-%d").date()
#                 except:
#                     return Response({"error": "Montant ou date invalide (format attendu : YYYY-MM-DD)."},
#                                     status=status.HTTP_400_BAD_REQUEST)
#                 prochaine_date = date_choisie

#         achats_client = Achat.objects.filter(ClientID_id=client_id)
#         if not achats_client.exists():
#             return Response({"error": "Aucun achat trouvé pour ce client."}, status=status.HTTP_404_NOT_FOUND)

#         total_attendu = sum(achat.ProduitID.Produit_prix * achat.Achat_quantite for achat in achats_client)
#         total_deja_paye = Paiement.objects.filter(AchatsID__ClientID_id=client_id).aggregate(
#             total=Sum('Paiement_montant')
#         )['total'] or Decimal('0')

#         nouveau_total = total_deja_paye + montant_paye
#         reste = max(total_attendu - nouveau_total, Decimal('0'))
#         statut = "complet" if nouveau_total >= total_attendu else "incomplet"
#         montant_rendu = int(nouveau_total - total_attendu) if nouveau_total > total_attendu else 0
#         revenu = int(nouveau_total - total_attendu) if nouveau_total > total_attendu else 0

#         dernier_achat = achats_client.order_by('-Achat_date').first()

#         # Génération du numéro de facture
#         # On cherche le dernier numéro de facture créé (le max des chiffres après "FACT-")
#         last_facture = Facture.objects.order_by('-id').first()
#         last_num = 0
#         if last_facture and last_facture.numero_facture:
#             import re
#             match = re.search(r'FACT-(\d+)', last_facture.numero_facture)
#             if match:
#                 last_num = int(match.group(1))
#         new_num = last_num + 1
#         numero_facture = f"FACT-{new_num:04d}"

#         facture = Facture.objects.create(achat=dernier_achat, numero_facture=numero_facture)

#         # Création du paiement
#         data = request.data.copy()
#         data['AchatsID'] = dernier_achat.id
#         data['Paiement_montant'] = montant_paye

#         if type_paiement == 'mensuel':
#             data['Paiement_montantchoisi'] = montant_choisi
#             data['Paiement_datechoisi'] = prochaine_date
#         else:
#             data.pop('Paiement_montantchoisi', None)
#             data.pop('Paiement_datechoisi', None)

#         serializer = self.get_serializer(data=data)
#         serializer.is_valid(raise_exception=True)
#         paiement = serializer.save()

#         # Envoi de SMS
#         client = dernier_achat.ClientID
#         numero = client.Client_telephone
#         envoyer_sms(numero, f"Bonjour {client.Client_nom}, votre paiement de {montant_paye:.0f} Ar a été reçu. "
#                             f"Statut: {statut}. Reste à payer: {reste:.0f} Ar.")

#         # Envoi email aux admins et vendeur
#         # responsable = dernier_achat.ResponsableID
#         # vendeur_email = responsable.Responsable_email
#         # admins = Responsable.objects.filter(Responsable_role='admin').values_list('Responsable_email', flat=True)
#         # envoyer_email(
#         #     sujet=f"Confirmation de paiement - {client.Client_nom}",
#         #     message=(
#         #         f"Le client {client.Client_nom} ({numero}) a effectué un paiement de {montant_paye:.0f} Ar.\n"
#         #         f"Statut : {statut}\nReste à payer : {reste:.0f} Ar.\n"
#         #         f"Revenu supplémentaire : {revenu:.0f} Ar.\n"
#         #     ),
#         #     destinataires=list(admins) + [vendeur_email],
#         #     reply_to=vendeur_email
#         # )

#         produits_achetes = [
#             {
#                 "nom": achat.ProduitID.Produit_nom,
#                 "quantite": achat.Achat_quantite,
#                 "prix_unitaire": int(achat.ProduitID.Produit_prix),
#                 "total": int(achat.ProduitID.Produit_prix * achat.Achat_quantite)
#             }
#             for achat in achats_client
#         ]

#         prixtotalproduit = sum(p["total"] for p in produits_achetes)
#         nombredemois_restant = int(reste / montant_choisi) if montant_choisi else None

#         return Response({
#             "repaiement": True if type_paiement == 'mensuel' and total_deja_paye > 0 else False,
#             "client": client.Client_nom,
#             "client_id": client.id,
#             "produits": produits_achetes,
#             "prixtotalproduit": prixtotalproduit,
#             "total_paye": int(nouveau_total),
#             "reste_a_payer": int(reste),
#             "montant_rendu": montant_rendu,
#             "revenu": revenu,
#             "statut": statut,
#             "Paiement_type": type_paiement,
#             "Paiement_montantchoisi": int(montant_choisi) if montant_choisi else None,
#             "nombredemois_restant": nombredemois_restant,
#             "date_paiement_prochaine": str(prochaine_date) if prochaine_date else None,
#             "numero_facture": facture.numero_facture,
#             "facture_id": facture.id,
#         }, status=status.HTTP_201_CREATED)


from decimal import Decimal
from datetime import datetime
from dateutil.relativedelta import relativedelta

from rest_framework import status, generics
from rest_framework.response import Response
from django.db.models import Sum

from .serializers import PaiementSerializer

from decimal import Decimal, InvalidOperation
from datetime import datetime
from dateutil.relativedelta import relativedelta
from rest_framework import status, generics
from rest_framework.response import Response
from django.db.models import Sum

class RepaiementCreateView(generics.CreateAPIView):
    queryset = Paiement.objects.all()
    serializer_class = PaiementSerializer

    def create(self, request, *args, **kwargs):
        client_id = request.data.get('client')
        if not client_id:
            return Response({"error": "Le champ 'client' est requis."}, status=status.HTTP_400_BAD_REQUEST)

        # Montant payé sécurisé
        montant_raw = request.data.get('Paiement_montant')
        try:
            montant_paye = Decimal(montant_raw)
            if montant_paye <= 0:
                raise InvalidOperation
        except (InvalidOperation, TypeError):
            return Response({"error": "Montant payé invalide."}, status=status.HTTP_400_BAD_REQUEST)

        # Type de paiement
        type_paiement = request.data.get('Paiement_type', '').lower()
        if type_paiement not in ['comptant', 'mensuel']:
            return Response({"error": "Type de paiement invalide."}, status=status.HTTP_400_BAD_REQUEST)

        # Tous les achats du client
        achats_client = Achat.objects.filter(ClientID_id=client_id)
        if not achats_client.exists():
            return Response({"error": "Aucun achat trouvé pour ce client."}, status=status.HTTP_404_NOT_FOUND)

        # Filtrer les achats incomplets
        achats_incomplets = []
        for achat in achats_client:
            total_paye = Paiement.objects.filter(AchatsID=achat.id).aggregate(total=Sum('Paiement_montant'))['total'] or Decimal('0')
            total_attendu = achat.ProduitID.Produit_prix * achat.Achat_quantite
            if total_paye < total_attendu:
                achats_incomplets.append(achat)

        if not achats_incomplets:
            return Response({"error": "Tous les achats de ce client sont déjà complets."}, status=status.HTTP_400_BAD_REQUEST)

        # On prend le premier achat incomplet
        dernier_achat = achats_incomplets[0]

        # Calcul du total attendu pour ce achat
        total_attendu = dernier_achat.ProduitID.Produit_prix * dernier_achat.Achat_quantite

        # Gestion du paiement mensuel
        montant_choisi = None
        prochaine_date = None
        if type_paiement == 'mensuel':
            dernier_paiement = Paiement.objects.filter(
                AchatsID__ClientID_id=client_id,
                Paiement_type='mensuel'
            ).order_by('-Paiement_date').first()

            if dernier_paiement and dernier_paiement.Paiement_montantchoisi:
                montant_choisi = dernier_paiement.Paiement_montantchoisi
                date_choisie = dernier_paiement.Paiement_datechoisi or datetime.today().date()
                mois_a_ajouter = int(montant_paye / montant_choisi) if montant_choisi > 0 else 0
                prochaine_date = date_choisie + relativedelta(months=mois_a_ajouter)
            else:
                montant_choisi = montant_paye
                prochaine_date = datetime.today().date()

        # Créer le paiement
        paiement_data = {
            'AchatsID': dernier_achat.id,
            'Paiement_montant': montant_paye,
            'Paiement_mode': request.data.get('Paiement_mode'),
            'Paiement_type': type_paiement,
        }
        if type_paiement == 'mensuel':
            paiement_data['Paiement_montantchoisi'] = montant_choisi
            paiement_data['Paiement_datechoisi'] = prochaine_date

        serializer = self.get_serializer(data=paiement_data)
        serializer.is_valid(raise_exception=True)
        paiement = serializer.save()

        # Total déjà payé sur tous les achats du client
        total_deja_paye = Paiement.objects.filter(
            AchatsID__ClientID_id=client_id
        ).aggregate(total=Sum('Paiement_montant'))['total'] or Decimal('0')

        # Montants restants pour ce paiement
        reste = max(total_attendu - total_deja_paye, Decimal('0'))
        statut = "complet" if total_deja_paye >= total_attendu else "incomplet"
        montant_rendu = int(total_deja_paye - total_attendu) if total_deja_paye > total_attendu else 0

        # Création de facture si absente
        facture, _ = Facture.objects.get_or_create(achat=dernier_achat)

        produits_achetes = [
            {
                "nom": achat.ProduitID.Produit_nom,
                "quantite": achat.Achat_quantite,
                "prix_unitaire": int(achat.ProduitID.Produit_prix),
                "total": int(achat.ProduitID.Produit_prix * achat.Achat_quantite)
            } for achat in achats_client
        ]
        prixtotalproduit = sum(p["total"] for p in produits_achetes)

        nombredemois_restant = int(reste / montant_choisi) if type_paiement == 'mensuel' and montant_choisi else None
        revenu_total = total_deja_paye

        return Response({
            "repaiement": type_paiement == 'mensuel' and total_deja_paye > 0,
            "client": dernier_achat.ClientID.Client_nom,
            "produits": produits_achetes,
            "prixtotalproduit": prixtotalproduit,
            "total_paye": int(total_deja_paye),
            "reste_a_payer": int(reste),
            "montant_rendu": montant_rendu,
            "statut": statut,
            "Paiement_type": type_paiement,
            "Paiement_montantchoisi": int(montant_choisi) if montant_choisi else None,
            "nombredemois_restant": nombredemois_restant,
            "date_paiement_prochaine": str(prochaine_date) if prochaine_date else None,
            "numero_facture": facture.numero_facture,
            "facture_id": facture.id,
            "revenu": int(montant_paye),
            "revenu_total": int(revenu_total)
        }, status=status.HTTP_201_CREATED)



class PaiementListView(generics.ListAPIView):
    queryset = Paiement.objects.all().order_by('-Paiement_date')
    serializer_class = PaiementSerializer 

from collections import defaultdict
from decimal import Decimal
from django.db.models import Sum, Max
from rest_framework.views import APIView
from rest_framework.response import Response

class ListeResteAPayerParClient(APIView):
    def get(self, request):
        clients = Client.objects.all()
        clients_map = {}  # clé = client.id, valeur = objet client regroupé

        for client in clients:
            achats = Achat.objects.filter(ClientID=client)
            if not achats.exists():
                continue

            total_attendu_client = Decimal('0')
            produits_totaux = []

            for achat in achats:
                produit = achat.ProduitID
                quantite = achat.Achat_quantite
                prix_unitaire = Decimal(produit.Produit_prix)
                total = prix_unitaire * quantite
                total_attendu_client += total

                # Fusionner les produits par nom si déjà existant
                exist_prod = next((p for p in produits_totaux if p["nom"] == produit.Produit_nom), None)
                if exist_prod:
                    exist_prod["quantite"] += quantite
                    exist_prod["total"] += int(total)
                else:
                    produits_totaux.append({
                        "nom": produit.Produit_nom,
                        "quantite": quantite,
                        "prix_unitaire": int(prix_unitaire),
                        "total": int(total)
                    })

            # Paiements du client
            paiements_client = Paiement.objects.filter(AchatsID__ClientID=client)
            total_paye = paiements_client.aggregate(total=Sum('Paiement_montant'))['total'] or Decimal('0')
            reste = max(total_attendu_client - total_paye, Decimal('0'))
            statut = "complet" if total_paye >= total_attendu_client else "incomplet"

            # Paiements mensuels
            paiements_mensuels = paiements_client.filter(Paiement_type='mensuel')
            prochaine_date = paiements_mensuels.aggregate(max_date=Max("Paiement_datechoisi"))['max_date']
            montant_choisi = paiements_mensuels.last().Paiement_montantchoisi if paiements_mensuels.exists() else None
            nombredemois_restant = int(reste / montant_choisi) if montant_choisi and montant_choisi > 0 else None
            progress = int((total_paye / total_attendu_client) * 100) if total_attendu_client > 0 else 0

            clients_map[client.id] = {
                "id": client.id,
                "client": client.Client_nom,
                "prenom": client.Client_prenom,
                "achats_par_date": [
                    {
                        "date": min(achat.Achat_date for achat in achats).strftime("%Y-%m-%d %H:%M:%S"),
                        "produits": produits_totaux
                    }
                ],
                "prixtotalproduit": int(total_attendu_client),
                "total_paye": int(total_paye),
                "reste_a_payer": int(reste),
                "montantchoisi": montant_choisi,
                "statut": statut,
                "progress": progress,
                "date_paiement_prochaine": str(prochaine_date) if prochaine_date else None,
                "nombredemois_restant": nombredemois_restant,
            }

        # Retourner la liste finale avec une "date globale" par client (ici date du premier achat)
        response_data = []
        for client_obj in clients_map.values():
            response_data.append({
                "date": client_obj["achats_par_date"][0]["date"],
                "clients": [client_obj]
            })

        return Response(response_data, status=200)



class VerifierPaiementListView(generics.ListAPIView):
    def get(self, request, *args, **kwargs):
        date_aujourdhui = date.today()
        notifications = []

        # 🔹 Parcours de tous les clients
        clients = Client.objects.all()
        for client in clients:
            paiements = Paiement.objects.filter(AchatsID__ClientID=client).order_by("Paiement_datechoisi")

            # ✅ Cas 1 : Aucun paiement encore enregistré
            

            # ✅ Cas 2 & 3 : Paiements existants → vérifier la prochaine échéance
            for paiement in paiements:
                date_utilisee = paiement.Paiement_datechoisi
                if not date_utilisee:
                    continue

                delta = date_utilisee - date_aujourdhui
                achat = paiement.AchatsID

                # Cas 2 : Paiement dans ≤ 5 jours
                if timedelta(days=0) <= delta <= timedelta(days=5):
                    message = (
                        f"Bonjour {client.Client_nom} {client.Client_prenom}, "
                        f"votre prochain paiement est prévu le {paiement.Paiement_datechoisi} "
                    )

                # Cas 3 : Paiement déjà dépassé → rappel quotidien
                elif date_aujourdhui > date_utilisee:
                    message = (
                        f"Bonjour {client.Client_nom} {client.Client_prenom}, "
                        f"vous avez dépassé la date prévue de paiement ({paiement.Paiement_datechoisi}). "
                        f"Merci de régulariser rapidement."
                    )
                else:
                    continue

                # Envoi du SMS
                if client.Client_telephone:
                    envoyer_sms(client.Client_telephone, message)

                notifications.append({
                    "message": message,
                    "client_id": client.id,
                    "achat_date": achat.Achat_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "date_paiement": str(date_utilisee),
                })

        return Response({"messages": notifications}, status=status.HTTP_200_OK)


from django.shortcuts import get_object_or_404
from django.utils.timezone import make_aware, is_naive
from django.db.models import Sum, Max
from django.http import JsonResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from urllib.parse import unquote
from datetime import datetime, timedelta
from decimal import Decimal

from decimal import Decimal
from datetime import timedelta
from urllib.parse import unquote
from dateutil.parser import parse as parse_date
from django.shortcuts import get_object_or_404
from django.utils.timezone import make_aware, is_naive
from django.db.models import Sum, Max
from rest_framework.views import APIView
from rest_framework.response import Response

from django.utils.dateparse import parse_date
from django.utils.timezone import make_aware, is_naive
from django.db.models import Sum, Max
from rest_framework.views import APIView
from rest_framework.response import Response
from urllib.parse import unquote
from datetime import timedelta
from decimal import Decimal
from django.shortcuts import get_object_or_404

from django.shortcuts import get_object_or_404
from django.utils.timezone import make_aware, is_naive
from django.db.models import Sum, Max
from rest_framework.views import APIView
from rest_framework.response import Response
from urllib.parse import unquote
from datetime import datetime
from decimal import Decimal

class ListePayerParClients(APIView):
    """
    Retourne tous les achats d'un client à partir d'une date donnée :
    - Produits achetés
    - Paiements effectués
    - Totaux et reste à payer
    - Statut et progression
    """
    def get(self, request, client_id, date_achat):
        client = get_object_or_404(Client, id=client_id)

        # Décodage de l'URL et parsing de la date avec heure
        try:
            date_str = unquote(date_achat)
            date_dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            if is_naive(date_dt):
                date_dt = make_aware(date_dt)
        except ValueError:
            return Response({"detail": "Format de date invalide. Utilisez YYYY-MM-DD HH:MM:SS."}, status=400)

        # Récupérer tous les achats à partir de cette date
        achats = Achat.objects.filter(
            ClientID=client,
            Achat_date__gte=date_dt
        ).order_by('Achat_date')

        if not achats.exists():
            return Response({"detail": "Aucun achat trouvé pour ce client à partir de cette date."}, status=404)

        # Récupérer tous les paiements liés à ces achats
        paiements = Paiement.objects.filter(AchatsID__in=achats).order_by('Paiement_date')
        total_paye = paiements.aggregate(total=Sum('Paiement_montant'))['total'] or Decimal('0.0')

        # Produits achetés
        produits = []
        for achat in achats:
            produit = achat.ProduitID
            quantite = achat.Achat_quantite
            prix_unitaire = float(produit.Produit_prix)
            total = prix_unitaire * quantite
            produits.append({
                "nom": produit.Produit_nom,
                "quantite": quantite,
                "prix_unitaire": prix_unitaire,
                "total": total
            })

        prixtotalproduit = sum(p["total"] for p in produits)
        reste = float(prixtotalproduit) - float(total_paye)
        statut = "complet" if reste <= 0 else "incomplet"

        # Paiements mensuels
        paiements_mensuels = paiements.filter(Paiement_type='mensuel')
        prochaine_date = paiements_mensuels.aggregate(max_date=Max("Paiement_datechoisi"))['max_date']
        montant_choisi = paiements_mensuels.last().Paiement_montantchoisi if paiements_mensuels.exists() else None
        nombredemois_restant = int(reste / float(montant_choisi)) if montant_choisi and montant_choisi > 0 else None

        paiements_data = [
            {
                "id": p.id,
                "montant": float(p.Paiement_montant),
                "date": p.Paiement_date.isoformat(),
                "responsable": p.AchatsID.ResponsableID.Responsable_email,
            }
            for p in paiements
        ]

        return Response({
            "client": {
                "photo": client.Client_photo.url if client.Client_photo else None,
                "nom": client.Client_nom,
                "prenom": client.Client_prenom,
                "telephone": client.Client_telephone,
                "telephone1": client.Client_telephone1,
                "telephone2": client.Client_telephone2,
                "telephone3": client.Client_telephone3,
                "telephone4": client.Client_telephone4,
                "adresse": client.Client_adresse,
                "cin": client.Client_cin,
            },
            "date_achat_debut": date_dt.isoformat(),
            "montantchoisi": montant_choisi,
            "produits": produits,
            "paiements": paiements_data,
            "prixtotalproduit": prixtotalproduit,
            "total_paye": float(total_paye),
            "reste_a_payer": reste,
            "statut": statut,
            "date_paiement_prochaine": str(prochaine_date) if prochaine_date else None,
            "nombredemois_restant": nombredemois_restant,
        })

from collections import defaultdict
from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Max
from rest_framework.views import APIView
from rest_framework.response import Response

from django.shortcuts import get_object_or_404
from django.utils.timezone import make_aware, is_naive
from django.db.models import Sum, Max
from rest_framework.views import APIView
from rest_framework.response import Response
from urllib.parse import unquote
from datetime import timedelta
from decimal import Decimal
from dateutil import parser

class ListePayerParClient(APIView):
    def get(self, request, client_id, date_achat=None):
        client = get_object_or_404(Client, id=client_id)

        # Si une date est fournie → on filtre sur la journée
        date_debut = None
        date_fin = None
        if date_achat:
            from dateutil import parser
            try:
                date_str = unquote(date_achat)
                date_dt = parser.parse(date_str)
                if is_naive(date_dt):
                    date_dt = make_aware(date_dt)
                date_debut = date_dt.replace(hour=0, minute=0, second=0, microsecond=0)
                date_fin = date_debut + timedelta(days=1)
            except Exception:
                return Response({"detail": "Format de date invalide."}, status=400)

        achats = Achat.objects.filter(ClientID=client)
        if date_debut and date_fin:
            achats = achats.filter(Achat_date__gte=date_debut, Achat_date__lt=date_fin)

        if not achats.exists():
            return Response({"detail": "Aucun achat trouvé pour ce client."}, status=404)

        # --- Produits regroupés ---
        produits = []
        prixtotalproduit = 0
        for achat in achats:
            produit = achat.ProduitID
            prix_unitaire = float(produit.Produit_prix)
            quantite = achat.Achat_quantite
            total = prix_unitaire * quantite
            prixtotalproduit += total

            produits.append({
                "nom": produit.Produit_nom,
                "quantite": quantite,
                "prix_unitaire": prix_unitaire,
                "total": total
            })

        # --- Paiements ---
        paiements = Paiement.objects.filter(AchatsID__in=achats).order_by("Paiement_date")
        total_paye = paiements.aggregate(total=Sum("Paiement_montant"))['total'] or Decimal("0.0")
        reste = float(prixtotalproduit) - float(total_paye)
        statut = "complet" if reste <= 0 else "incomplet"

        paiements_mensuels = paiements.filter(Paiement_type="mensuel")
        prochaine_date = paiements_mensuels.aggregate(max_date=Max("Paiement_datechoisi"))['max_date']
        montant_choisi = paiements_mensuels.last().Paiement_montantchoisi if paiements_mensuels.exists() else None
        nombredemois_restant = int(reste / float(montant_choisi)) if montant_choisi and montant_choisi > 0 else None
        progress = int((float(total_paye) / float(prixtotalproduit)) * 100) if prixtotalproduit > 0 else 0

        return Response({
            "id": client.id,
            "photo": client.Client_photo.url if client.Client_photo else None,
            "client": client.Client_nom,
            "prenom": client.Client_prenom,
            "telephone": client.Client_telephone,
            "telephone1": client.Client_telephone1,
            "telephone2": client.Client_telephone2,
            "telephone3": client.Client_telephone3,
            "telephone4": client.Client_telephone4,
            "adresse": client.Client_adresse,
            "cin": client.Client_cin,
            "achats_par_date": [
                {
                    "date": date_debut.strftime("%Y-%m-%d") if date_debut else "tous",
                    "produits": produits
                }
            ],
            "prixtotalproduit": prixtotalproduit,
            "total_paye": float(total_paye),
            "reste_a_payer": reste,
            "montantchoisi": montant_choisi,
            "statut": statut,
            "progress": progress,
            "date_paiement_prochaine": str(prochaine_date) if prochaine_date else None,
            "nombredemois_restant": nombredemois_restant,
        })


class SmsVerifierByClientView(APIView):
    def get(self, request, client_id):
        try:
            client = Client.objects.get(id=client_id)
        except Client.DoesNotExist:
            return Response({"error": "Client non trouvé."}, status=status.HTTP_404_NOT_FOUND)

        paiements = Paiement.objects.filter(AchatsID__ClientID=client)

        today = date.today()
        notifications = []

        for paiement in paiements:
            date_choisi = paiement.Paiement_datechoisi
            if not date_choisi:
                continue

            delta = date_choisi - today

            if timedelta(days=0) <= delta <= timedelta(days=5):
                message = (
                    f"Bonjour {client.Client_nom}, votre prochain paiement est prévu le "
                    f"{date_choisi.strftime('%d/%m/%Y')}."
                )
                try:
                    if client.Client_telephone:
                        envoyer_sms(client.Client_telephone, message)
                        notifications.append({"message": message, "paiement_id": paiement.id})
                except Exception as e:
                    notifications.append({"error": str(e), "paiement_id": paiement.id})

        if not notifications:
            return Response({"info": "Aucun paiement proche à notifier."})

        return Response({"notifications": notifications})

class PaiementDeleteAPIView(APIView):
    def delete(self, request, paiement_id, format=None):
        try:
            paiement = Paiement.objects.get(pk=paiement_id)
        except Paiement.DoesNotExist:
            return Response({"error": "Paiement non trouvé."}, status=status.HTTP_404_NOT_FOUND)

        achat = paiement.AchatsID
        client = achat.ClientID

        # Sauvegarder le montant du paiement avant suppression
        montant_supprime = paiement.Paiement_montant

        # Supprimer le paiement
        paiement.delete()

        # Recalculer le total payé après suppression
        total_paye = achat.paiements_details.aggregate(
            total=Sum('Paiement_montant')
        )['total'] or Decimal('0')

        total_attendu = achat.ProduitID.Produit_prix * achat.Achat_quantite
        reste = max(total_attendu - total_paye, Decimal('0'))
        statut = "complet" if total_paye >= total_attendu else "incomplet"

        return Response({
            "message": "Paiement supprimé avec succès.",
            "client": client.Client_nom,
            "produit": achat.ProduitID.Produit_nom,
            "quantite": achat.Achat_quantite,
            "total_attendu": float(total_attendu),
            "total_paye": float(total_paye),
            "reste_a_payer": float(reste),
            "statut": statut,
            "montant_supprime": float(montant_supprime),
        }, status=status.HTTP_200_OK)


class PaiementUpdateView(generics.UpdateAPIView):
    queryset = Paiement.objects.all()
    serializer_class = PaiementSerializer

    def update(self, request, *args, **kwargs):
        paiement = self.get_object()
        client_id = request.data.get('client')

        if not client_id:
            return Response({"error": "Le champ 'client' est requis."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            montant_paye = Decimal(request.data.get('Paiement_montant', paiement.Paiement_montant))
        except:
            return Response({"error": "Le montant payé est invalide."}, status=status.HTTP_400_BAD_REQUEST)

        if montant_paye < Decimal('50000'):
            return Response({"error": "Le montant minimum à payer est de 100 000 Ariary."},
                            status=status.HTTP_400_BAD_REQUEST)

        type_paiement = request.data.get('Paiement_type', paiement.Paiement_type).lower()
        if type_paiement not in ['comptant', 'mensuel']:
            return Response({"error": "Type de paiement invalide."}, status=status.HTTP_400_BAD_REQUEST)

        montant_choisi = None
        date_choisie = None
        prochaine_date = None

        if type_paiement == 'mensuel':
            montant_choisi_str = request.data.get('Paiement_montantchoisi')
            date_choisie_str = request.data.get('Paiement_datechoisi')

            if not date_choisie_str:
                return Response({
                    "error": "La date choisie est requise pour un paiement mensuel."
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                date_choisie = datetime.strptime(str(date_choisie_str), "%Y-%m-%d").date()
                prochaine_date = date_choisie
            except:
                return Response({"error": "Date invalide (format attendu : YYYY-MM-DD)."},
                                status=status.HTTP_400_BAD_REQUEST)

            # Conserver le montant existant si non fourni
            try:
                montant_choisi = Decimal(montant_choisi_str) if montant_choisi_str else paiement.Paiement_montantchoisi
            except:
                return Response({"error": "Montant mensuel invalide."}, status=status.HTTP_400_BAD_REQUEST)

        else:
            request.data.pop('Paiement_montantchoisi', None)
            request.data.pop('Paiement_datechoisi', None)

        achats_client = Achat.objects.filter(ClientID_id=client_id)
        if not achats_client.exists():
            return Response({"error": "Aucun achat trouvé pour ce client."}, status=status.HTTP_404_NOT_FOUND)

        dernier_achat = achats_client.order_by('-Achat_date').first()

        data = request.data.copy()
        data['AchatsID'] = dernier_achat.id
        data['Paiement_montant'] = montant_paye

        if type_paiement == 'mensuel':
            data['Paiement_montantchoisi'] = montant_choisi
            data['Paiement_datechoisi'] = prochaine_date

        serializer = self.get_serializer(paiement, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        total_attendu = sum(achat.ProduitID.Produit_prix * achat.Achat_quantite for achat in achats_client)
        total_deja_paye = Paiement.objects.filter(AchatsID__ClientID_id=client_id).aggregate(
            total=Sum('Paiement_montant')
        )['total'] or Decimal('0')

        nouveau_total = total_deja_paye
        reste = max(total_attendu - nouveau_total, Decimal('0'))
        statut = "complet" if nouveau_total >= total_attendu else "incomplet"
        montant_rendu = int(nouveau_total - total_attendu) if nouveau_total > total_attendu else 0

        client = dernier_achat.ClientID
        numero = client.Client_telephone

        # Notification SMS
        envoyer_sms(numero, f"Bonjour {client.Client_nom}, votre paiement de {montant_paye:.0f} Ar a été mis à jour. "
                            f"Statut: {statut}. Reste à payer: {reste:.0f} Ar.")

        # # Email aux responsables
        # responsable = dernier_achat.ResponsableID
        # vendeur_email = responsable.Responsable_email
        # admins = Responsable.objects.filter(Responsable_role='admin').values_list('Responsable_email', flat=True)

        # Optionnel : Décommente pour activer l'email
        # envoyer_email(
        #     sujet=f"Mise à jour du paiement - {client.Client_nom}",
        #     message=(f"Le client {client.Client_nom} ({numero}) a modifié un paiement de {montant_paye:.0f} Ar.\n"
        #              f"Statut : {statut}\nReste à payer : {reste:.0f} Ar.\n"),
        #     destinataires=list(admins) + [vendeur_email],
        #     reply_to=vendeur_email
        # )

        produits_achetes = [
            {
                "nom": achat.ProduitID.Produit_nom,
                "quantite": achat.Achat_quantite,
                "prix_unitaire": int(achat.ProduitID.Produit_prix),
                "total": int(achat.ProduitID.Produit_prix * achat.Achat_quantite)
            }
            for achat in achats_client
        ]

        prixtotalproduit = sum(p["total"] for p in produits_achetes)
        nombredemois_restant = int(reste / montant_choisi) if montant_choisi else None

        return Response({
            "client": {
                "nom": client.Client_nom,
                "telephone": client.Client_telephone,
                "adresse": client.Client_adresse,
                "cin": client.Client_cin,
            },
            "produits": produits_achetes,
            "prixtotalproduit": prixtotalproduit,
            "total_paye": int(nouveau_total),
            "reste_a_payer": int(reste),
            "montant_rendu": montant_rendu,
            "statut": statut,
            "Paiement_type": type_paiement,
            "Paiement_montantchoisi": int(montant_choisi) if montant_choisi else None,
            "nombredemois_restant": nombredemois_restant,
            "date_paiement_prochaine": str(prochaine_date) if prochaine_date else None
        }, status=status.HTTP_200_OK)


from django.db.models import F, Sum, ExpressionWrapper, DecimalField
class ChiffreAffairesAPIView(APIView):
    def get(self, request):
        # 1. Chiffre d'affaires réel (paiements enregistrés)
        total_ca = Paiement.objects.aggregate(
            total=Sum('Paiement_montant')
        )['total'] or 0

        # 2. Total attendu : quantité * prix produit
        achats = Achat.objects.annotate(
            total=ExpressionWrapper(
                F('Achat_quantite') * F('ProduitID__Produit_prix'),
                output_field=DecimalField()
            )
        )

        total_attendu = sum([a.total for a in achats])

        # 3. Différence (reste dû)
        montant_restant = total_attendu - total_ca

        return Response({
            "chiffre_affaires": float(total_ca),
            "montant_total_attendu": float(total_attendu),
            "montant_restant_du": float(montant_restant) if montant_restant > 0 else 0.0
        })


from decimal import Decimal
from collections import defaultdict
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class PaiementView(APIView):
    def get(self, request):
        # Récupérer tous les paiements
        paiements = Paiement.objects.select_related('AchatsID__ClientID', 'AchatsID__ProduitID', 'AchatsID__ResponsableID').all().order_by('Paiement_date')

        # Regrouper les paiements par facture
        factures_map = defaultdict(lambda: {
            "facture_id": None,
            "numero_facture": None,
            "date_creation": None,
            "client": None,
            "telephone": None,
            "responsable": None,
            "produits": [],
            "prixtotalproduit": Decimal('0'),
            "total_paye": Decimal('0'),
            "reste_a_payer": Decimal('0'),
            "statut": "incomplet",
            "paiements": []
        })

        for paiement in paiements:
            achat = paiement.AchatsID
            facture = Facture.objects.filter(achat=achat).first()
            client = achat.ClientID
            responsable = achat.ResponsableID

            if not facture:
                continue  # ignorer si pas de facture

            key = facture.id  # clé = facture_id
            f = factures_map[key]

            f["facture_id"] = facture.id
            f["numero_facture"] = facture.numero_facture
            f["date_creation"] = facture.date_creation
            f["client"] = client.Client_nom
            f["telephone"] = client.Client_telephone
            f["responsable"] = {
                "id": responsable.id,
                "nom": responsable.Responsable_nom,
                "telephone_res": responsable.Responsable_telephone
            }

            # Ajouter produit si pas déjà présent
            produit_total = achat.ProduitID.Produit_prix * achat.Achat_quantite
            if not any(p['nom'] == achat.ProduitID.Produit_nom for p in f["produits"]):
                f["produits"].append({
                    "nom": achat.ProduitID.Produit_nom,
                    "quantite": achat.Achat_quantite,
                    "prix_unitaire": int(achat.ProduitID.Produit_prix),
                    "total": int(produit_total)
                })
                f["prixtotalproduit"] += produit_total

            # Ajouter le paiement
            f["paiements"].append({
                "id": paiement.id,
                "AchatsID": achat.id,
                "Paiement_montant": str(paiement.Paiement_montant),
                "date": paiement.Paiement_date.isoformat()
            })

            # Calculer total payé et reste
            f["total_paye"] += paiement.Paiement_montant
            f["reste_a_payer"] = max(f["prixtotalproduit"] - f["total_paye"], Decimal('0'))
            f["statut"] = "complet" if f["total_paye"] >= f["prixtotalproduit"] else "incomplet"

        # Transformer en liste
        result = list(factures_map.values())

        # Convertir les Decimals en int pour JSON
        for f in result:
            f["prixtotalproduit"] = int(f["prixtotalproduit"])
            f["total_paye"] = int(f["total_paye"])
            f["reste_a_payer"] = int(f["reste_a_payer"])

        return Response(result, status=status.HTTP_200_OK)




from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import PaiementMobile
from .services import initier_paiement_sandbox

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

# @csrf_exempt
# def lancer_paiement(request):
#     if request.method == "POST":
#         # Récupération des données JSON
#         import json
#         body = json.loads(request.body)
#         numero_client = body.get("numero_client")
#         montant = body.get("montant")
        
#         # Ici tu peux simuler le paiement sandbox
#         return JsonResponse({
#             "message": f"✅ Paiement sandbox initié pour {numero_client}, montant: {montant} Ar"
#         })
#     else:
#         return JsonResponse({"error": "Méthode non autorisée"}, status=405)

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Paiement
import json

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from .models import Paiement, Achat  # ⚠️ Vérifie bien le nom du modèle (Achat ou Achats)

@csrf_exempt
def lancer_paiement(request):
    if request.method != "POST":
        return JsonResponse({"error": "Méthode non autorisée"}, status=405)

    try:
        data = json.loads(request.body)

        id_achat = data.get("idachat")  # 👈 récupère l’id de l’achat envoyé depuis le frontend
        numero_client = data.get("numero_client")
        montant = data.get("montant")
        mode = data.get("mode", "mvola")
        numero_entreprise = data.get("numero_entreprise", "0340000001")
        description = data.get("description", "")

        # Vérifie si l’achat existe
        if not id_achat:
            return JsonResponse({"error": "idachat manquant"}, status=400)

        try:
            achat = Achat.objects.get(id=id_achat)
        except Achat.DoesNotExist:
            return JsonResponse({"error": f"Achat id={id_achat} introuvable"}, status=404)

        # Création du paiement lié à l’achat
        paiement = Paiement.objects.create(
            AchatsID=achat,  # 🔥 clé étrangère obligatoire
            numero_client=numero_client,
            Paiement_montant=montant,
            Paiement_mode=mode,
            numero_entreprise=numero_entreprise,
            statut="en_attente"
        )

        # Simulation du paiement
        message = paiement.verifier_paiement_mobile()

        return JsonResponse({
            "message": message,
            "transaction_reference": paiement.transaction_reference,
            "statut": paiement.statut,
            "id_achat": achat.id,
            "numero_client": paiement.numero_client,
            "montant": paiement.Paiement_montant
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
def paiement_callback(request):
    """MVola envoie ici le statut final du paiement"""
    if request.method == "POST":
        data = json.loads(request.body)
        transaction_ref = data.get("requestingOrganisationTransactionReference")
        statut_mv = data.get("transactionStatus")  # ex: "SUCCESSFUL" ou "FAILED"

        try:
            paiement = PaiementMobile.objects.get(transaction_reference=transaction_ref)
        except PaiementMobile.DoesNotExist:
            return JsonResponse({"error": "Transaction non trouvée"}, status=404)

        if statut_mv == "SUCCESSFUL":
            paiement.statut = "reussi"
        else:
            paiement.statut = "echoue"

        paiement.save()
        return JsonResponse({"message": "Statut mis à jour"})

    return JsonResponse({"error": "Méthode non autorisée"}, status=405)
