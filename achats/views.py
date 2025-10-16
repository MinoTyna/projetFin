from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from django.conf import settings
from .models import Achat, Produit, Facture, Responsable
from .serializers import AchatReadSerializer, AchatWriteSerializer
from decimal import Decimal
from django.db.models import Sum, F
from datetime import datetime
import calendar
from .models import Facture
from paiement.models import Paiement 
from paiement.serializers import PaiementSerializer  # Assure-toi que c'est bien importé
from django.utils.dateparse import parse_date
from django.utils.timezone import localtime
from django.db.models.functions import TruncDate,TruncMonth
from django.db.models import Prefetch


from traceback import format_exc

class EnregistrerAchatAPIView(APIView):
    def post(self, request):
        try:
            data = request.data
            client_id = data.get("ClientID")
            responsable_id = data.get("ResponsableID")
            achats_data = data.get("achats", [])

            if not client_id or not responsable_id:
                return Response({"error": "ClientID et ResponsableID sont requis"}, status=400)

            if not achats_data:
                return Response({"error": "Aucun achat fourni"}, status=400)

            achats_enregistres = []
            montant_total_global = Decimal("0.00")
            stock_temp = {}

            for achat in achats_data:
                produit_id = achat.get("ProduitID")
                quantite_achat = achat.get("Achat_quantite")

                if not produit_id or not quantite_achat:
                    return Response(
                        {"error": "ProduitID et Achat_quantite requis pour chaque achat"}, status=400
                    )

                try:
                    produit = Produit.objects.get(id=produit_id)
                except Produit.DoesNotExist:
                    return Response({"error": f"Produit {produit_id} introuvable"}, status=404)

                deja_reserve = stock_temp.get(produit_id, 0)
                stock_restant = produit.Produit_quantite - deja_reserve

                if stock_restant < quantite_achat:
                    return Response(
                        {
                            "error": f"Stock insuffisant pour '{produit.Produit_nom}'. "
                                     f"Disponible: {stock_restant}, demandé: {quantite_achat}"
                        },
                        status=400,
                    )

                montant_achat = Decimal(produit.Produit_prix) * Decimal(quantite_achat)
                montant_total_global += montant_achat

                # Vérifier si le client a déjà acheté ce produit
                achat_existant = Achat.objects.filter(ClientID_id=client_id, ProduitID_id=produit_id).first()

                if achat_existant:
                    # Cumuler la quantité et le montant
                    achat_existant.Achat_quantite += quantite_achat
                    achat_existant.Achat_montant += montant_achat
                    achat_existant.save()
                    achats_enregistres.append(achat_existant)
                else:
                    serializer = AchatWriteSerializer(
                        data={
                            "ClientID": client_id,
                            "ResponsableID": responsable_id,
                            "ProduitID": produit_id,
                            "Achat_quantite": quantite_achat,
                            "Achat_montant": montant_achat,
                        }
                    )
                    if serializer.is_valid():
                        achat_instance = serializer.save()
                        achats_enregistres.append(achat_instance)
                    else:
                        return Response(serializer.errors, status=400)

                stock_temp[produit_id] = deja_reserve + quantite_achat

            # Mise à jour du stock
            for produit_id, quantite_total in stock_temp.items():
                produit = Produit.objects.get(id=produit_id)
                produit.Produit_quantite -= quantite_total
                produit.save()

                if produit.Produit_quantite < 3:
                    responsable = achats_enregistres[0].ResponsableID
                    send_mail(
                        subject=f"Stock bas pour {produit.Produit_nom}",
                        message=f"Le stock de '{produit.Produit_nom}' est faible ({produit.Produit_quantite}).",
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[responsable.Responsable_email],
                        fail_silently=True,
                    )

            if not achats_enregistres:
                return Response({"error": "Aucun achat valide enregistré"}, status=400)

            # Regrouper tous les achats en un seul panier
            panier = {
                "client_id": achats_enregistres[0].ClientID.id,
                "client": achats_enregistres[0].ClientID.Client_nom,  # adapte selon ton modèle
                "responsable": achats_enregistres[0].ResponsableID.Responsable_email,
                "achats": [
                    {
                        "produit": achat.ProduitID.Produit_nom,
                        "quantite": achat.Achat_quantite,
                        "prix_total": achat.Achat_montant,
                    }
                    for achat in achats_enregistres
                ],
                "total_general": montant_total_global,
            }

            return Response(panier, status=201)

        except Exception as e:
            # Retourner l'erreur complète pour debug
            return Response({
                "error": str(e),
                "trace": format_exc()
            }, status=500)

class ListAchatAPIView(APIView):
    def get(self, request, client_id):
        achats = Achat.objects.filter(ClientID=client_id).order_by('-Achat_date')
        serializer = AchatReadSerializer(achats, many=True, context={'request': request})

        total = sum(
            achat.ProduitID.Produit_prix * achat.Achat_quantite for achat in achats
        )

        return Response({
            "achats": serializer.data,
            "total_achats": total
        }, status=status.HTTP_200_OK)

class AchatListAPIView(APIView):
    def get(self, request):
        achats = Achat.objects.all()
        serializer = AchatReadSerializer(achats, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class AchatDeleteAPIView(APIView):
    def delete(self, request, achat_id):
        try:
            achat = Achat.objects.get(id=achat_id)
        except Achat.DoesNotExist:
            return Response({"error": "Achat introuvable."}, status=status.HTTP_404_NOT_FOUND)

        produit = achat.ProduitID  # 🔁 Corrigé ici

        # ✅ Rendre la quantité au stock
        produit.Produit_quantite += achat.Achat_quantite
        produit.save()

        achat.delete()

        return Response({
            "message": "Achat supprimé avec succès.",
            "stock_restitue": f"{achat.Achat_quantite} unité(s) rendue(s) à '{produit.Produit_nom}'",
            "stock_actuel": produit.Produit_quantite
        }, status=status.HTTP_200_OK)

# class FactureHistoriqueView(APIView):
#     def get(self, request, pk):
#         try:
#             facture = Facture.objects.get(pk=pk)
#         except Facture.DoesNotExist:
#             return Response({"error": "Facture non trouvée."}, status=status.HTTP_404_NOT_FOUND)

#         client = facture.achat.ClientID
#         responsable = facture.achat.ResponsableID

#         achats = facture.achat.ClientID.achat_set.all()
#         produits = [
#             {
#                 "nom": achat.ProduitID.Produit_nom,
#                 "quantite": achat.Achat_quantite,
#                 "prix_unitaire": int(achat.ProduitID.Produit_prix),
#                 "total": int(achat.ProduitID.Produit_prix * achat.Achat_quantite),
#             }
#             for achat in achats
#         ]
#         prixtotalproduit = sum(p["total"] for p in produits)

#         paiements = facture.achat.paiements_details.all().order_by('Paiement_date')

#         historique_etats = []
#         total_paye_cumul = Decimal('0')

#         for paiement in paiements:
#             total_paye_cumul += paiement.Paiement_montant
#             reste = max(prixtotalproduit - total_paye_cumul, Decimal('0'))
#             statut = "complet" if reste == 0 else "incomplet"

#             historique_etats.append({
#                 "numero_facture": facture.numero_facture,
#                 "date_creation": paiement.Paiement_date.date().isoformat(),
#                 "client": client.Client_nom,
#                 "telephone": client.Client_telephone,
#                 "responsable": {
#                     "id": responsable.id,
#                     "nom": responsable.Responsable_nom,
#                     "telephone_res": responsable.Responsable_telephone,
#                 },
#                 "produits": produits,
#                 "prixtotalproduit": prixtotalproduit,
#                 "total_paye": float(total_paye_cumul),
#                 "reste_a_payer": float(reste),
#                 "statut": statut,
#                 "paiement_detail": {
#                     "date": paiement.Paiement_date,
#                     "montant": float(paiement.Paiement_montant),
#                 }
#             })

#         return Response(historique_etats)
from datetime import timedelta




# class FactureAllView(APIView):
#     def get(self, request):
#         factures = Facture.objects.all()
#         all_factures_data = []

#         for facture in factures:
#             if not facture.achat:
#                 continue  # Ignore les factures sans achat

#             achat = facture.achat
#             client = achat.ClientID
#             responsable = achat.ResponsableID
#             achats = client.achat_set.all()

#             produits = [
#                 {
#                     "nom": achat.ProduitID.Produit_nom,
#                     "quantite": achat.Achat_quantite,
#                     "prix_unitaire": int(achat.ProduitID.Produit_prix),
#                     "total": int(achat.ProduitID.Produit_prix * achat.Achat_quantite),
#                 }
#                 for achat in achats
#             ]

#             prixtotalproduit = sum(p["total"] for p in produits)
#             paiements = achat.paiements_details.all().order_by('Paiement_date')
#             total_paye = sum(p.Paiement_montant for p in paiements)
#             reste = max(prixtotalproduit - total_paye, Decimal('0'))
#             statut = "complet" if reste == 0 else "incomplet"

#             all_factures_data.append({
#                 "facture_id": facture.id,
#                 "numero_facture": facture.numero_facture,
#                 "date_creation": facture.date_creation.date().isoformat(),
#                 "client": client.Client_nom,
#                 "telephone": client.Client_telephone,
#                 "responsable": {
#                     "id": responsable.id,
#                     "nom": responsable.Responsable_nom,
#                     "telephone_res": responsable.Responsable_telephone,
#                 },
#                 "produits": produits,
#                 "prixtotalproduit": prixtotalproduit,
#                 "total_paye": float(total_paye),
#                 "reste_a_payer": float(reste),
#                 "statut": statut,
#             })

#         return Response(all_factures_data, status=status.HTTP_200_OK)

from collections import defaultdict
from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from .models import Facture

from django.db.models import Sum
from collections import defaultdict
from traceback import format_exc

class FactureAllView(APIView):
    def get(self, request):
        try:
            factures = Facture.objects.all().select_related(
                'achat__ClientID', 'achat__ResponsableID', 'achat__ProduitID'
            ).prefetch_related('achat__paiements_details', 'achat__ProduitID')

            clients_data = {}

            for facture in factures:
                if not facture.achat:
                    continue

                client = facture.achat.ClientID
                responsable = facture.achat.ResponsableID
                client_key = client.id

                achats = Achat.objects.filter(ClientID=client)
                paiements = Paiement.objects.filter(AchatsID__in=achats).order_by('Paiement_date')

                # Grouper les produits identiques
                produits_grouped = defaultdict(lambda: {"quantite": 0, "prix_unitaire": 0})
                for achat in achats:
                    nom = achat.ProduitID.Produit_nom
                    produits_grouped[nom]["quantite"] += achat.Achat_quantite
                    produits_grouped[nom]["prix_unitaire"] = float(achat.ProduitID.Produit_prix)

                produits = []
                prixtotalproduit = Decimal('0')
                for nom, data in produits_grouped.items():
                    total = Decimal(data["prix_unitaire"]) * data["quantite"]
                    prixtotalproduit += total
                    produits.append({
                        "nom": nom,
                        "quantite": data["quantite"],
                        "prix_unitaire": data["prix_unitaire"],
                        "total": float(total)
                    })

                # Total payé et reste
                total_paye = paiements.aggregate(total=Sum('Paiement_montant'))['total'] or Decimal('0')
                reste = prixtotalproduit - total_paye
                statut = "complet" if reste <= 0 else "incomplet"

                # Date d'achat : prendre la première date d'achat disponible
                date_achat = achats.order_by('Achat_date').first()
                date_achat_str = date_achat.Achat_date.strftime('%Y-%m-%d %H:%M:%S') if date_achat else None

                clients_data[client_key] = {
                    "client": getattr(client, "Client_nom", ""),
                    "prenom": getattr(client, "Client_prenom", ""),
                    "client_id": client.id,
                    "telephone": getattr(client, "Client_telephone", ""),
                    "Client_adresse": getattr(client, "Client_adresse", ""),
                    "responsable": {
                        "id": getattr(responsable, "id", None),
                        "nom": getattr(responsable, "Responsable_nom", ""),
                        "prenomres": getattr(responsable, "Responsable_prenom", ""),
                        "telephone_res": getattr(responsable, "Responsable_telephone", ""),
                    },
                    "produits": produits,
                    "prixtotalproduit": float(prixtotalproduit),
                    "total_paye": float(total_paye),
                    "reste_a_payer": float(reste),
                    "statut": statut,
                    "date_achat": date_achat_str,
                    "paiements_detail": [
                        {
                            "date": p.Paiement_date.strftime('%Y-%m-%d %H:%M:%S'),
                            "montant": float(p.Paiement_montant)
                        } for p in paiements
                    ]
                }

            response_data = list(clients_data.values())
            return Response(response_data, status=200)

        except Exception as e:
            return Response({
                "error": str(e),
                "trace": format_exc()
            }, status=500)
      
      
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from collections import defaultdict
from decimal import Decimal
from django.db.models import Sum
import traceback
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from collections import defaultdict
from decimal import Decimal
from django.db.models import Sum
from client.models import Client 

class FactureDates(APIView):
    def get(self, request, client_id):
        try:
            client = get_object_or_404(Client, id=client_id)

            achats = Achat.objects.filter(ClientID=client).select_related('ProduitID', 'ResponsableID')
            if not achats.exists():
                return Response({"detail": "Aucun achat trouvé pour ce client."}, status=404)

            # Récupérer le dernier achat du client
            dernier_achat = achats.order_by('-Achat_date').first()

            # Générer numéro de facture
            last_facture = Facture.objects.order_by('-id').first()
            last_num = 0
            if last_facture and last_facture.numero_facture:
                import re
                match = re.search(r'FACT-(\d+)', last_facture.numero_facture)
                if match:
                    last_num = int(match.group(1))
            new_num = last_num + 1
            numero_facture = f"FACT-{new_num:04d}"

            # Créer la facture associée au dernier achat
            facture = Facture.objects.create(achat=dernier_achat, numero_facture=numero_facture)

            # Groupe les produits identiques
            from collections import defaultdict
            from decimal import Decimal

            produits_grouped = defaultdict(lambda: {"quantite": 0, "prix_unitaire": 0})
            for achat in achats:
                if not achat.ProduitID:
                    continue
                nom = achat.ProduitID.Produit_nom
                produits_grouped[nom]["quantite"] += achat.Achat_quantite
                produits_grouped[nom]["prix_unitaire"] = float(achat.ProduitID.Produit_prix)

            produits = []
            prixtotalproduit = Decimal('0')
            for nom, data in produits_grouped.items():
                total = Decimal(data["prix_unitaire"]) * data["quantite"]
                prixtotalproduit += total
                produits.append({
                    "nom": nom,
                    "quantite": data["quantite"],
                    "prix_unitaire": data["prix_unitaire"],
                    "total": float(total)
                })

            paiements = Paiement.objects.filter(AchatsID__in=achats).order_by('Paiement_date')
            total_paye = paiements.aggregate(total=Sum('Paiement_montant'))['total'] or Decimal('0')
            reste = prixtotalproduit - total_paye
            statut = "complet" if reste <= 0 else "incomplet"

            date_achat = dernier_achat
            date_achat_str = date_achat.Achat_date.strftime('%Y-%m-%d %H:%M:%S') if date_achat else None

            responsable = dernier_achat.ResponsableID
            responsable_data = {
                "id": responsable.id if responsable else None,
                "nom": responsable.Responsable_nom if responsable else "",
                "prenomres": responsable.Responsable_prenom if responsable else "",
                "telephone_res": responsable.Responsable_telephone if responsable else "",
            }

            paiements_detail = [
                {
                    "date": p.Paiement_date.strftime('%Y-%m-%d %H:%M:%S'),
                    "montant": float(p.Paiement_montant)
                } for p in paiements
            ]

            response_data = {
                "client": client.Client_nom,
                "prenom": client.Client_prenom,
                "client_id": client.id,
                "telephone": client.Client_telephone,
                "Client_adresse": client.Client_adresse,
                "responsable": responsable_data,
                "produits": produits,
                "prixtotalproduit": float(prixtotalproduit),
                "total_paye": float(total_paye),
                "reste_a_payer": float(reste),
                "statut": statut,
                "numero_facture": facture.numero_facture,
                "date_achat": date_achat_str,
                "paiements_detail": paiements_detail
            }

            return Response(response_data, status=200)

        except Exception as e:
            import traceback
            return Response({
                "error": str(e),
                "trace": traceback.format_exc()
            }, status=500)


class FactureDetailView(APIView):
    def get(self, request, facture_id):
        try:
            facture = Facture.objects.select_related(
                'achat__ClientID', 'achat__ResponsableID', 'achat__ProduitID'
            ).prefetch_related('achat__paiements_details').get(id=facture_id)
        except Facture.DoesNotExist:
            return Response({"error": "Facture non trouvée"}, status=status.HTTP_404_NOT_FOUND)

        achat = facture.achat
        if not achat:
            return Response({"error": "Achat non lié à la facture"}, status=status.HTTP_400_BAD_REQUEST)

        client = achat.ClientID
        responsable = achat.ResponsableID
        paiements = achat.paiements_details.all().order_by('Paiement_date')

        produits = [{
            "nom": achat.ProduitID.Produit_nom,
            "quantite": achat.Achat_quantite,
            "prix_unitaire": int(achat.ProduitID.Produit_prix),
            "total": int(achat.ProduitID.Produit_prix * achat.Achat_quantite),
        }]

        prixtotalproduit = sum(p["total"] for p in produits)
        total_paye_cumul = Decimal(0)
        response_data = []

        for paiement in paiements:
            total_paye_cumul += paiement.Paiement_montant
            reste = max(prixtotalproduit - total_paye_cumul, Decimal('0'))
            revenu = max(total_paye_cumul - prixtotalproduit, Decimal('0'))
            statut = "complet" if reste == 0 else "incomplet"

            facture_data = {
                "numero_facture": facture.numero_facture,
                "date_creation": paiement.Paiement_date.strftime('%Y-%m-%d %H:%M:%S'),
                "client": client.Client_nom,
                "prenom": client.Client_prenom,
                "telephone": client.Client_telephone,
                "responsable": {
                    "id": responsable.id,
                    "nom": responsable.Responsable_nom,
                    "prenomres": responsable.Responsable_prenom,
                    "telephone_res": responsable.Responsable_telephone,
                },
                "produits": produits,
                "prixtotalproduit": prixtotalproduit,
                "total_paye": float(total_paye_cumul),
                "reste_a_payer": float(reste),
                "revenu": float(revenu),
                "statut": statut,
                "paiement_detail": {
                    "date": paiement.Paiement_date.strftime('%Y-%m-%d %H:%M:%S'),
                    "montant": float(paiement.Paiement_montant)
                }
            }

            response_data.append(facture_data)

        return Response(response_data, status=status.HTTP_200_OK)



class FactureDate(APIView):
    def get(self, request):
        date_param = request.GET.get("date")  # exemple: "09/2023" ou "septembre 2023"

        factures = Facture.objects.all()

        if date_param:
            try:
                if "/" in date_param:
                    # format "MM/YYYY"
                    month_str, year_str = date_param.split("/")
                    month = int(month_str)
                    year = int(year_str)
                else:
                    # format "septembre 2023"
                    parts = date_param.lower().split()
                    if len(parts) == 2:
                        month_name = parts[0]
                        year = int(parts[1])
                        month = list(calendar.month_name).index(month_name.capitalize())
                    else:
                        return Response({"error": "Format de date invalide."}, status=400)

                factures = factures.filter(date_creation__year=year, date_creation__month=month)
            except Exception as e:
                return Response({"error": f"Erreur de traitement de la date: {str(e)}"}, status=400)

        all_factures_data = []

        for facture in factures:
            client = facture.achat.ClientID
            responsable = facture.achat.ResponsableID
            achats = client.achat_set.all()

            produits = [
                {
                    "nom": achat.ProduitID.Produit_nom,
                    "quantite": achat.Achat_quantite,
                    "prix_unitaire": int(achat.ProduitID.Produit_prix),
                    "total": int(achat.ProduitID.Produit_prix * achat.Achat_quantite),
                }
                for achat in achats
            ]

            prixtotalproduit = sum(p["total"] for p in produits)
            paiements = facture.achat.paiements_details.all().order_by('Paiement_date')
            total_paye = sum(p.Paiement_montant for p in paiements)
            reste = max(prixtotalproduit - total_paye, Decimal('0'))
            statut = "complet" if reste == 0 else "incomplet"

            all_factures_data.append({
                "facture_id": facture.id,
                "numero_facture": facture.numero_facture,
                "date_creation": facture.date_creation.date().isoformat(),
                "client": client.Client_nom,
                "telephone": client.Client_telephone,
                "responsable": {
                    "id": responsable.id,
                    "nom": responsable.Responsable_nom,
                    "telephone_res": responsable.Responsable_telephone,
                },
                "produits": produits,
                "prixtotalproduit": prixtotalproduit,
                "total_paye": float(total_paye),
                "reste_a_payer": float(reste),
                "statut": statut,
            })

        return Response(all_factures_data, status=status.HTTP_200_OK)

class PaiementListView(APIView):
    def get(self, request):
        date_str = request.GET.get('date')  # ex: "07/2025"
        if not date_str:
            return Response({"error": "Le paramètre 'date' est requis. Format attendu : MM/AAAA."}, status=400)

        try:
            mois, annee = date_str.split('/')
            mois, annee = int(mois), int(annee)
        except ValueError:
            return Response({"error": "Format de date invalide. Utilisez MM/AAAA."}, status=400)

        paiements = Paiement.objects.filter(
            Paiement_date__month=mois,
            Paiement_date__year=annee
        ).order_by("-Paiement_date")

        resultats = []
        for paiement in paiements:
            achat = paiement.AchatsID
            client = achat.ClientID
            responsable = achat.ResponsableID
            produits = achat.ProduitID.all() if hasattr(achat.ProduitID, 'all') else [achat.ProduitID]

            # Si tu as plusieurs paiements pour un même achat, calcule le total payé
            paiements_achat = Paiement.objects.filter(AchatsID=achat)
            montant_total_paye = sum(p.Paiement_montant for p in paiements_achat)
            montant_total_choisi = paiements_achat.last().Paiement_montantchoisi if paiements_achat.exists() else 0
            reste = montant_total_choisi - montant_total_paye
            statut = "complet" if reste <= 0 else "incomplet"

            data = {
                "paiement": {
                    "id": paiement.id,
                    "AchatsID": achat.id,
                    "Paiement_montant": str(paiement.Paiement_montant),
                    "Paiement_montantchoisi": str(paiement.Paiement_montantchoisi),
                    "Paiement_mode": paiement.Paiement_mode,
                    "Paiement_type": paiement.Paiement_type,
                    "Paiement_date": paiement.Paiement_date,
                    "Paiement_datechoisi": paiement.Paiement_datechoisi
                },
                "facture": {
                    "facture_id": achat.id,
                    "numero_facture": f"FACT-{achat.id}",
                    "date_creation": str(achat.Achat_date),
                    "client": client.Client_nom,
                    "telephone": client.Client_telephone,
                    "responsable": {
                        "id": responsable.id,
                        "nom": responsable.Responsable_nom,
                        "email": responsable.Responsable_email
                    },
                    "produits": [
                        {
                            "nom": produit.Produit_nom,
                            "quantite": achat.Achat_quantite,
                            "prix_unitaire": float(produit.Produit_prix),
                            "total": float(produit.Produit_prix) * achat.Achat_quantite
                        }
                        for produit in produits
                    ],
                    "prixtotalproduit": sum(
                        float(produit.Produit_prix) * achat.Achat_quantite
                        for produit in produits
                    ),
                    "Paiement_montant": montant_total_paye,
                    "reste_a_payer": reste,
                    "statut": statut
                }
            }

            resultats.append(data)

        return Response(resultats, status=status.HTTP_200_OK)

# class PaiementListView(APIView):
#     def get(self, request):
#         date_param = request.GET.get("date")
#         paiements = Paiement.objects.all()

#         if date_param:
#             try:
#                 if "/" in date_param:
#                     month_str, year_str = date_param.split("/")
#                     month = int(month_str)
#                     year = int(year_str)
#                 else:
#                     parts = date_param.lower().split()
#                     month = list(calendar.month_name).index(parts[0].capitalize())
#                     year = int(parts[1])
#                 paiements = paiements.filter(Paiement_date__year=year, Paiement_date__month=month)
#             except Exception as e:
#                 return Response({"error": f"Date invalide: {str(e)}"}, status=400)

#         data = []

#         for p in paiements:
#             achat = p.AchatsID
#             client = achat.ClientID
#             responsable = achat.ResponsableID
#             produit = achat.ProduitID

#             # Calcul du total payé pour cet achat
#             paiements_achat = Paiement.objects.filter(AchatsID=achat)
#             total_paye = paiements_achat.aggregate(total=Sum("Paiement_montantchoisi"))["total"] or 0

#             reste_a_payer = float(produit.Produit_prix) - float(total_paye)

#             paiement_data = {
#                 "id": p.id,
#                 "AchatsID": achat.id,
#                 "Paiement_montant": str(p.Paiement_montant),
#                 "Paiement_montantchoisi": str(p.Paiement_montantchoisi),
#                 "Paiement_mode": p.Paiement_mode,
#                 "Paiement_type": p.Paiement_type,
#                 "Paiement_date": p.Paiement_date,
#                 "Paiement_datechoisi": p.Paiement_datechoisi,
#                 "statut": "complet" if reste_a_payer <= 0 else "incomplet",
#                 "reste_a_payer": reste_a_payer,
#                 # "nombredemois_restant": p.nombredemois_restant,
#             }

#             facture_data = {
#                 "facture_id": achat.id,
#                 "numero_facture": f"FACT-{achat.id}",
#                 "date_creation": achat.Achat_date.strftime("%Y-%m-%d"),
#                 "client": client.Client_nom,
#                 "telephone": client.Client_telephone,
#                 "responsable": {
#                     "id": responsable.id,
#                     "nom": responsable.Responsable_nom,
#                     "email": responsable.Responsable_email
#                 },
#                 "produits": [
#                     {
#                         "nom": produit.Produit_nom,
#                         "quantite": achat.Achat_quantite,
#                         "prix_unitaire": float(produit.Produit_prix),
#                         "total": float(produit.Produit_prix) * achat.Achat_quantite
#                     }
#                 ],
#                 "prixtotalproduit": float(produit.Produit_prix) * achat.Achat_quantite,
#                 "total_paye": float(total_paye),
#                 "reste_a_payer": reste_a_payer,
#                 "statut": "complet" if reste_a_payer <= 0 else "incomplet"
#             }

#             data.append({
#                 "paiement": paiement_data,
#                 "facture": facture_data
#             })

#         return Response(data, status=status.HTTP_200_OK)


# class PaiementListView(APIView):
#     def get(self, request):
#         date_param = request.GET.get("date")
#         paiements = Paiement.objects.all()

#         if date_param:
#             try:
#                 if "/" in date_param:
#                     # Format: MM/YYYY
#                     month_str, year_str = date_param.split("/")
#                     month = int(month_str)
#                     year = int(year_str)
#                 else:
#                     # Format: mois en texte (ex: juillet 2025)
#                     parts = date_param.lower().split()
#                     month = list(calendar.month_name).index(parts[0].capitalize())
#                     year = int(parts[1])

#                 paiements = paiements.filter(Paiement_date__year=year, Paiement_date__month=month)
#             except Exception as e:
#                 return Response({"error": f"Date invalide: {str(e)}"}, status=400)

#         data = []
#         for p in paiements:
#             serializer = PaiementSerializer(p)
#             serialized_data = serializer.data  # dictionnaire contenant tous les champs

#             data.append({
#                 "id": p.id,
#                 "AchatsID": p.AchatsID.id,
#                 "Paiement_montant": str(p.Paiement_montant),
#                 "Paiement_montantchoisi": str(p.Paiement_montantchoisi),
#                 "Paiement_mode": p.Paiement_mode,
#                 "Paiement_type": p.Paiement_type,
#                 "Paiement_date": p.Paiement_date,
#                 "Paiement_datechoisi": p.Paiement_datechoisi,
#                 "statut": serialized_data["statut"],
#                 "reste_a_payer": serialized_data["reste_a_payer"],
#                 "nombredemois_restant": serialized_data["nombredemois_restant"],
#             })

#         return Response(data, status=status.HTTP_200_OK)



# class PaiementListView(APIView):
#     def get(self, request):
#         date_param = request.GET.get("date")
#         paiements = Paiement.objects.all()

#         if date_param:
#             try:
#                 if "/" in date_param:
#                     # Format: MM/YYYY
#                     month_str, year_str = date_param.split("/")
#                     month = int(month_str)
#                     year = int(year_str)
#                 else:
#                     # Format: mois en texte (ex: juillet 2025)
#                     parts = date_param.lower().split()
#                     month = list(calendar.month_name).index(parts[0].capitalize())
#                     year = int(parts[1])

#                 paiements = paiements.filter(Paiement_date__year=year, Paiement_date__month=month)
#             except Exception as e:
#                 return Response({"error": f"Date invalide: {str(e)}"}, status=400)

#         data = []
#         for p in paiements:
#             data.append({
#                 "id": p.id,
#                 "AchatsID": p.AchatsID.id,
#                 "Paiement_montant": str(p.Paiement_montant),
#                 "Paiement_montantchoisi": str(p.Paiement_montantchoisi),
#                 "Paiement_mode": p.Paiement_mode,
#                 "Paiement_type": p.Paiement_type,
#                 "Paiement_date": p.Paiement_date,
#                 "Paiement_datechoisi": p.Paiement_datechoisi,
#                 "statut": p.statut,
#                 "reste_a_payer": float(p.reste_a_payer),
#                 "nombredemois_restant": p.nombredemois_restant
#             })

#         return Response(data, status=status.HTTP_200_OK)



class ProduitSortieTotalAPIView(APIView):
    def get(self, request):
        total_sortie = Achat.objects.aggregate(total=Sum("Achat_quantite"))["total"] or 0
        total_stock = Produit.objects.aggregate(total=Sum("Produit_quantite"))["total"] or 0
        total_produit = total_sortie + total_stock

        return Response({
            "total_sortie": total_sortie,
            "total_restant": total_stock,
            "total_produit": total_produit,
        }, status=status.HTTP_200_OK)
    




class ProduitSortieTotalAPI(APIView):
    def get(self, request):
        # Sorties par produit
        sorties_par_produit = (
            Achat.objects.values('ProduitID__Produit_nom')
            .annotate(sortie=Sum('Achat_quantite'))
        )

        # Stock par produit
        stock_par_produit = (
            Produit.objects.values('Produit_nom')
            .annotate(stock=Sum('Produit_quantite'))
        )

        # Fusion des données
        data = {}
        for item in sorties_par_produit:
            nom = item['ProduitID__Produit_nom']
            data[nom] = {
                'sortie': item['sortie'],
                'stock': 0
            }

        for item in stock_par_produit:
            nom = item['Produit_nom']
            if nom in data:
                data[nom]['stock'] = item['stock']
            else:
                data[nom] = {
                    'stock': item['stock'],
                    'sortie': 0
                }

        # Ajout du champ "entrer"
        result = [
            {
                'produit': nom,
                'sortie': valeurs['sortie'],
                'stock': valeurs['stock'],
                'entrer': (valeurs['sortie'] or 0) + (valeurs['stock'] or 0)
            }
            for nom, valeurs in data.items()
        ]

        return Response(result, status=status.HTTP_200_OK)


class ProduitPlusVenduAPIView(APIView):
    def get(self, request):
        produits_ventes = (
            Achat.objects
            .values("ProduitID")
            .annotate(total_vendu=Sum("Achat_quantite"))
            .order_by("-total_vendu")[:5]  # Top 5
        )

        result = []
        for p in produits_ventes:
            try:
                produit = Produit.objects.get(id=p["ProduitID"])
                result.append({
                    "produit_nom": produit.Produit_nom,
                    "quantite_vendue": p["total_vendu"]
                })
            except Produit.DoesNotExist:
                continue

        return Response(result, status=status.HTTP_200_OK)
    
# class ProduitPlusVenduAPIView(APIView):
#     def get(self, request):
#         data = (
#             Achat.objects
#             .annotate(mois=TruncMonth('Achat_date'))
#             .values('mois', 'ProduitID__Produit_nom')
#             .annotate(quantite_vendue=Sum('Achat_quantite'))
#             .order_by('mois')
#         )

#         # Format des dates pour affichage (ex: "07-2025")
#         results = []
#         for entry in data:
#             results.append({
#                 "mois": entry["mois"].strftime("%m-%Y"),
#                 "produit": entry["ProduitID__Produit_nom"],
#                 "quantite_vendue": entry["quantite_vendue"]
#             })

#         return Response(results)
class TotalAchatsParResponsableAPIView(APIView):
    def get(self, request, responsable_id):
        totals = Achat.objects.filter(ResponsableID=responsable_id).aggregate(
            total_quantite=Sum('Achat_quantite'),
            total_montant=Sum('Achat_montant')
        )

        return Response({
            "responsable_id": responsable_id,
            "total_quantite": totals['total_quantite'] or 0,
            "total_montant": totals['total_montant'] or 0
        }, status=status.HTTP_200_OK)
    


class ProduitsParResponsableAPIView(APIView):
    def get(self, request):
        data = []

        responsables = Responsable.objects.all()

        for responsable in responsables:
            # Filtrer les achats par responsable
            achats = Achat.objects.filter(ResponsableID=responsable)

            # Obtenir les produits distincts
            produits = achats.values_list('ProduitID__Produit_nom', flat=True).distinct()

            data.append({
                'responsable': responsable.Responsable_nom,  # adapte selon ton modèle
                'nombre_produits': produits.count(),
                'produits': list(produits)
            })

        return Response(data, status=status.HTTP_200_OK)


class ClientsFidelesAPIView(APIView):
    def get(self, request):
        achats = Achat.objects.select_related('ClientID', 'ProduitID')

        stats_clients = {}

        for achat in achats:
            client = achat.ClientID
            date_str = achat.Achat_date.strftime('%d-%m-%Y')
            montant = achat.ProduitID.Produit_prix * achat.Achat_quantite
            quantite = achat.Achat_quantite

            if client.id not in stats_clients:
                stats_clients[client.id] = {
                    'client_nom': client.Client_nom,
                    'client_prenom': client.Client_prenom,
                    'achats_par_date': {},
                    'total_montant': 0.0,
                }

            if date_str not in stats_clients[client.id]['achats_par_date']:
                stats_clients[client.id]['achats_par_date'][date_str] = {
                    'total_produits_achetes': 0,
                    'total_depense': 0.0
                }

            stats_clients[client.id]['achats_par_date'][date_str]['total_produits_achetes'] += quantite
            stats_clients[client.id]['achats_par_date'][date_str]['total_depense'] += float(montant)

            # Mise à jour du total_montant global du client
            stats_clients[client.id]['total_montant'] += float(montant)

        result = []
        for client_data in stats_clients.values():
            achats_par_date_list = []
            for date, stats in sorted(client_data['achats_par_date'].items()):
                achats_par_date_list.append({
                    'date': date,
                    'total_produits_achetes': stats['total_produits_achetes'],
                    'total_depense': stats['total_depense']
                })
            result.append({
                'client_nom': client_data['client_nom'],
                'client_prenom': client_data['client_prenom'],
                'achats_par_date': achats_par_date_list,
                'total_montant': client_data['total_montant']
            })

        return Response(result)
# class StatistiquesResponsableAPIView(APIView):
#     def get(self, request):
#         data = []

#         responsables = Responsable.objects.all()

#         for responsable in responsables:
#             achats = Achat.objects.filter(ResponsableID=responsable)

#             produits = achats.values_list('ProduitID__Produit_nom', flat=True).distinct()
#             nombre_produits = produits.count()

#             # Extraire les dates d'achat distinctes
#             dates = (
#                 achats
#                 .annotate(date=TruncDate('Achat_date'))
#                 .values_list('date', flat=True)
#                 .distinct()
#                 .order_by('date')
#             )

#             stats_par_jour = []
#             for date in dates:
#                 achats_du_jour = achats.filter(Achat_date__date=date)

#                 montant_total = 0
#                 quantite_total = 0
#                 produits_jour_set = set()

#                 for achat in achats_du_jour:
#                     prix_unitaire = achat.ProduitID.Produit_prix
#                     quantite = achat.Achat_quantite
#                     montant_total += prix_unitaire * quantite
#                     quantite_total += quantite
#                     produits_jour_set.add(achat.ProduitID.Produit_nom)

#                 stats_par_jour.append({
#                     'date': date,
#                     'montant_total': float(montant_total),
#                     'quantite_total': quantite_total,
#                     'produits': list(produits_jour_set)
#                 })

#             data.append({
#                 'responsable': responsable.Responsable_nom,
#                 'nombre_produits': nombre_produits,
#                 'produits': list(produits),
#                 'stats_par_jour': stats_par_jour
#             })

#         return Response(data, status=status.HTTP_200_OK)

class StatistiquesResponsableAPIView(APIView):
    def get(self, request):
        data = []

        responsables = Responsable.objects.all()

        for responsable in responsables:
            achats = Achat.objects.filter(ResponsableID=responsable).select_related('ProduitID')

            produits = achats.values_list('ProduitID__Produit_nom', flat=True).distinct()
            nombre_produits = produits.count()

            # ========================
            # 📆 Statistiques par jour
            # ========================
            dates = (
                achats
                .annotate(date=TruncDate('Achat_date'))
                .values_list('date', flat=True)
                .distinct()
                .order_by('date')
            )

            stats_par_jour = []
            for date in dates:
                achats_du_jour = achats.filter(Achat_date__date=date)

                montant_total = 0
                quantite_total = 0
                produits_jour_set = set()

                for achat in achats_du_jour:
                    prix_unitaire = achat.ProduitID.Produit_prix
                    quantite = achat.Achat_quantite
                    montant_total += prix_unitaire * quantite
                    quantite_total += quantite
                    produits_jour_set.add(achat.ProduitID.Produit_nom)

                stats_par_jour.append({
                    'date': date.strftime('%d-%m-%Y'),
                    'montant_total': float(montant_total),
                    'quantite_total': quantite_total,
                    'produits': list(produits_jour_set)
                })

            # ==========================
            # 📅 Statistiques par mois
            # ==========================
            mois_list = (
                achats
                .annotate(mois=TruncMonth('Achat_date'))
                .values_list('mois', flat=True)
                .distinct()
                .order_by('mois')
            )

            stats_par_mois = []
            for mois in mois_list:
                achats_du_mois = achats.filter(Achat_date__month=mois.month, Achat_date__year=mois.year)

                montant_total = 0
                quantite_total = 0
                produits_mois_set = set()

                for achat in achats_du_mois:
                    prix_unitaire = achat.ProduitID.Produit_prix
                    quantite = achat.Achat_quantite
                    montant_total += prix_unitaire * quantite
                    quantite_total += quantite
                    produits_mois_set.add(achat.ProduitID.Produit_nom)

                stats_par_mois.append({
                    'mois': mois.strftime('%m-%Y'),
                    'montant_total': float(montant_total),
                    'quantite_total': quantite_total,
                    'produits': list(produits_mois_set)
                })

            # 🔽 Résultat final par responsable
            data.append({
                'responsable': responsable.Responsable_nom,
                'nombre_produits': nombre_produits,
                'produits': list(produits),
                'stats_par_jour': stats_par_jour,
                'stats_par_mois': stats_par_mois,  # ✅ Ajout ici
            })

        return Response(data, status=200)
    


class StatistiquesResponsableAPI(APIView):
    def get(self, request):
        data = []

        responsables = Responsable.objects.all()

        for responsable in responsables:
            achats = Achat.objects.filter(ResponsableID=responsable).select_related('ProduitID')

            produits = achats.values_list('ProduitID__Produit_nom', flat=True).distinct()
            nombre_produits = produits.count()

            # 📆 Statistiques par jour
            dates = (
                achats
                .annotate(date=TruncDate('Achat_date'))
                .values_list('date', flat=True)
                .distinct()
                .order_by('date')
            )

            stats_par_jour = []
            for date in dates:
                achats_du_jour = achats.filter(Achat_date__date=date)

                montant_total = 0
                quantite_total = 0
                produits_jour_set = set()

                for achat in achats_du_jour:
                    prix_unitaire = achat.ProduitID.Produit_prix
                    quantite = achat.Achat_quantite
                    montant_total += prix_unitaire * quantite
                    quantite_total += quantite
                    produits_jour_set.add(achat.ProduitID.Produit_nom)

                stats_par_jour.append({
                    'date': date.strftime('%d-%m-%Y'),
                    'montant_total': float(montant_total),
                    'quantite_total': quantite_total,
                    'produits': list(produits_jour_set)
                })

            # 📅 Statistiques par mois
            mois_list = (
                achats
                .annotate(mois=TruncMonth('Achat_date'))
                .values_list('mois', flat=True)
                .distinct()
                .order_by('mois')
            )

            stats_par_mois = []
            for mois in mois_list:
                achats_du_mois = achats.filter(Achat_date__month=mois.month, Achat_date__year=mois.year)

                montant_total = 0
                quantite_total = 0
                produits_mois_set = set()

                for achat in achats_du_mois:
                    prix_unitaire = achat.ProduitID.Produit_prix
                    quantite = achat.Achat_quantite
                    montant_total += prix_unitaire * quantite
                    quantite_total += quantite
                    produits_mois_set.add(achat.ProduitID.Produit_nom)

                stats_par_mois.append({
                    'mois': mois.strftime('%m-%Y'),
                    'montant_total': float(montant_total),
                    'quantite_total': quantite_total,
                    'produits': list(produits_mois_set)
                })

            # 🔽 Résultat par responsable
            data.append({
                'responsable': responsable.Responsable_nom,
                'nombre_produits': nombre_produits,
                'produits': list(produits),
                'stats_par_jour': stats_par_jour,
                'stats_par_mois': stats_par_mois,
            })

        # 🌐 Statistiques Globales par Mois (tous achats confondus)
        achats_tous = Achat.objects.select_related('ProduitID')
        mois_global = (
            achats_tous
            .annotate(mois=TruncMonth('Achat_date'))
            .values('mois')
            .annotate(
                montant_total=Sum(F('Achat_quantite') * F('ProduitID__Produit_prix'))
            )
            .order_by('mois')
        )

        global_par_mois = [
            {
                "mois": item["mois"].strftime('%m-%Y'),
                "montant_total": float(item["montant_total"]),
            }
            for item in mois_global
        ]

        return Response({
            "par_responsable": data,
            "global_par_mois": global_par_mois
        }, status=200)


class UpdateAchatsAPIView(APIView):
    def put(self, request, client_id):
        data = request.data
        responsable_id = data.get("ResponsableID")
        achats_data = data.get("achats", [])

        if not achats_data:
            return Response({"error": "Aucun achat fourni"}, status=status.HTTP_400_BAD_REQUEST)

        # 🔄 Récupérer les anciens achats
        anciens_achats = Achat.objects.filter(ClientID_id=client_id)

        # 🔄 Restituer le stock
        for achat in anciens_achats:
            produit = achat.ProduitID
            produit.Produit_quantite += achat.Achat_quantite
            produit.save()

        # 🔄 Supprimer les anciens achats
        anciens_achats.delete()

        # 🔄 Créer les nouveaux
        achats_enregistres = []
        montant_total_global = Decimal("0.00")
        stock_temp = {}

        for achat in achats_data:
            produit_id = achat.get("ProduitID")
            quantite_achat = achat.get("Achat_quantite")

            try:
                produit = Produit.objects.get(id=produit_id)
            except Produit.DoesNotExist:
                return Response({"error": f"Produit {produit_id} introuvable"}, status=status.HTTP_404_NOT_FOUND)

            deja_reserve = stock_temp.get(produit_id, 0)
            stock_restant = produit.Produit_quantite - deja_reserve

            if stock_restant < quantite_achat:
                return Response({
                    "error": f"Stock insuffisant pour {produit.Produit_nom}. Disponible: {stock_restant}, demandé: {quantite_achat}"
                }, status=status.HTTP_400_BAD_REQUEST)

            montant_achat = Decimal(produit.Produit_prix) * Decimal(quantite_achat)
            montant_total_global += montant_achat

            achat_data = {
                "ClientID": client_id,
                "ResponsableID": responsable_id,
                "ProduitID": produit_id,
                "Achat_quantite": quantite_achat,
                "Achat_montant": montant_achat,
            }

            serializer = AchatWriteSerializer(data=achat_data)
            serializer.is_valid(raise_exception=True)
            achat_instance = serializer.save()
            achats_enregistres.append(achat_instance)

            stock_temp[produit_id] = deja_reserve + quantite_achat

        # 🔄 Mise à jour réelle du stock
        for produit_id, quantite_total in stock_temp.items():
            produit = Produit.objects.get(id=produit_id)
            produit.Produit_quantite -= quantite_total
            produit.save()

        achats_serializer = AchatReadSerializer(achats_enregistres, many=True)
        return Response({
            "achats": achats_serializer.data,
            "montant_total_session": montant_total_global
        }, status=status.HTTP_200_OK)


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Notification
from client.models import Client
from produit.models import Produit

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Notification,NotificationProduit
from client.models import Client
from produit.models import Produit



class ValiderCommande(APIView):
    def post(self, request):
        try:
            client_id = request.data.get('client_id')
            produits_data = request.data.get('produits') or []
            mode_reception = request.data.get('mode_reception')

            if not client_id or not produits_data or not mode_reception:
                return Response(
                    {'error': 'client_id, produits et mode_reception sont requis'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            client = Client.objects.get(id=client_id)

            # Créer la notification principale
            notif = Notification.objects.create(
                client=client,
                mode_reception=mode_reception
            )

            produits_list = []
            for p_data in produits_data:
                produit_id = p_data.get("id")
                quantite = p_data.get("quantite", 1)
                produit = Produit.objects.get(id=produit_id)

                # Ajouter le produit à la notification
                NotificationProduit.objects.create(
                    notification=notif,
                    produit=produit,
                    quantite=quantite
                )

                produits_list.append({
                    "id": produit.id,
                    "nom": produit.Produit_nom,
                    "prix": produit.Produit_prix,
                    "photo": produit.Produit_photo.url if produit.Produit_photo else None,
                    "quantite": quantite
                })

            return Response({
                'success': 'Commande validée',
                'notification': {
                    "id": notif.id,
                    "client": {
                        "id": client.id,
                        "nom": client.Client_nom,
                        "prenom": client.Client_prenom
                    },
                    "produits": produits_list,
                    "created_at": notif.created_at,
                    "mode_reception": notif.mode_reception
                }
            }, status=status.HTTP_200_OK)

        except Client.DoesNotExist:
            return Response({'error': 'Client non trouvé'}, status=status.HTTP_404_NOT_FOUND)
        except Produit.DoesNotExist:
            return Response({'error': 'Produit non trouvé'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {"error": "Erreur interne du serveur", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Notification
from .serializers import NotificationSerializer

class NotificationList(APIView):
    pagination_class = None  # désactive la pagination

    def get(self, request):
        notifications = Notification.objects.all().order_by('-created_at')
        data = []

        for notif in notifications:
            produits_list = []
            for np in notif.produits.all():  # related_name de NotificationProduit
                produits_list.append({
                    "id": np.produit.id,
                    "nom": np.produit.Produit_nom,
                    "prix": np.produit.Produit_prix,
                    "photo": np.produit.Produit_photo.url if np.produit.Produit_photo else None,
                    "quantite": np.quantite
                })

            data.append({
                "id": notif.id,
                "created_at": notif.created_at,
                "vue_client": notif.vue_client,
                "mode_reception": notif.mode_reception,
                "client": {
                    "id": notif.client.id,
                    "nom": notif.client.Client_nom,
                    "prenom": notif.client.Client_prenom,
                    "email": notif.client.Client_email,
                    "telephone": notif.client.Client_telephone,
                    "adresse": notif.client.Client_adresse,
                    "photo": notif.client.Client_photo.url if notif.client.Client_photo else None,
                },
                "produits": produits_list
            })

        return Response(data, status=status.HTTP_200_OK)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Notification, NotificationProduit

class AccepterNotification(APIView):
    """
    Accepter une notification côté admin et marquer la commande comme vue côté admin
    Affiche tous les produits avec leur quantité dans le message
    """
    def post(self, request, pk):
        # Récupérer la notification ou renvoyer 404
        notif = get_object_or_404(Notification, id=pk)

        # Marquer la notification comme vue côté admin
        notif.vue = True
        # Ne pas toucher à vue_client
        notif.save()

        # Nom du client
        client_nom = notif.client.Client_nom
        client_prenom = notif.client.Client_prenom

        # Récupérer tous les produits liés à cette notification
        produits_list = [
            f"{np.quantite} x {np.produit.Produit_nom}" for np in notif.produits.all()
        ]
        produits_str = ", ".join(produits_list) if produits_list else "aucun produit"

        # Construire le message
        message = f"La commande de {client_nom} {client_prenom} ({produits_str}) a été acceptée."

        # Retourner la réponse
        return Response(
            {"success": "Commande acceptée", "message": message},
            status=status.HTTP_200_OK
        )

from django.db.models import Q

class NotificationAccepteesParClient(APIView):
    def get(self, request, client_id):
        notifications = Notification.objects.filter(
            Q(client_id=client_id) & Q(Q(vue=True) | Q(vue_client=True))
        ).order_by('-created_at')

        if not notifications.exists():
            return Response(
                {"message": "Aucune notification acceptée pour ce client."},
                status=status.HTTP_200_OK
            )

        data = []
        for n in notifications:
            produits_list = []
            for np in n.produits.all():
                produits_list.append({
                    "id": np.produit.id,
                    "nom": np.produit.Produit_nom,
                    "prix": np.produit.Produit_prix,
                    "photo": np.produit.Produit_photo.url if np.produit.Produit_photo else None,
                    "quantite": np.quantite
                })

            data.append({
                "id": n.id,
                "message": "Votre commande est validée.",
                "created_at": n.created_at,
                "vue_client": n.vue_client,
                "mode_reception": n.mode_reception,
                "client": {
                    "id": n.client.id,
                    "nom": n.client.Client_nom,
                    "prenom": n.client.Client_prenom,
                    "email": n.client.Client_email,
                    "telephone": getattr(n.client, "Client_telephone", None),
                    "adresse": getattr(n.client, "Client_adresse", None),
                    "photo": n.client.Client_photo.url if n.client.Client_photo else None
                },
                "produits": produits_list
            })

        return Response(data, status=status.HTTP_200_OK)


class MarkNotificationReadClient(APIView):
    def post(self, request, notification_id):
        notif = get_object_or_404(Notification, id=notification_id)
        notif.vue_client = True
        # Ne rien toucher à notif.vue
        notif.save(update_fields=["vue_client"])  # 🔹 seulement mettre à jour vue_client
        return Response({"message": "Notification marquée comme lue"}, status=200)


    

class NotificationDetailById(APIView):
    def get(self, request, notif_id):
        try:
            notif = Notification.objects.get(id=notif_id)
        except Notification.DoesNotExist:
            return Response({"error": "Notification non trouvée"}, status=status.HTTP_404_NOT_FOUND)

        produits = []
        for np in notif.produits.all():
            produits.append({
                "id": np.produit.id,
                "nom": np.produit.Produit_nom,
                "prix": np.produit.Produit_prix,
                "photo": np.produit.Produit_photo.url if np.produit.Produit_photo else None,
                "quantite": np.quantite
            })

        data = {
            "id": notif.id,
            "created_at": notif.created_at,
            "vue_client": notif.vue_client,
            "mode_reception": notif.mode_reception,
            "client": {
                "id": notif.client.id,
                "nom": notif.client.Client_nom,
                "prenom": notif.client.Client_prenom,
                "email": notif.client.Client_email,
                "telephone": notif.client.Client_telephone,
                "adresse": notif.client.Client_adresse,
                "photo": notif.client.Client_photo.url if notif.client.Client_photo else None,
            },
            "produits": produits
        }

        return Response(data, status=status.HTTP_200_OK)
