from rest_framework import serializers
from .models import Paiement
from decimal import Decimal
from django.db.models import Sum

class PaiementSerializer(serializers.ModelSerializer):
    statut = serializers.SerializerMethodField()
    reste_a_payer = serializers.SerializerMethodField()
    nombredemois_restant = serializers.SerializerMethodField()
    revenu = serializers.SerializerMethodField()  # ✅ Nouveau champ

    class Meta:
        model = Paiement
        fields = [
            'id',
            'AchatsID',
            'Paiement_montant',
            'Paiement_montantchoisi',
            'Paiement_mode',
            'Paiement_type',
            'Paiement_date',
            'Paiement_datechoisi',
            'statut',
            'reste_a_payer',
            'nombredemois_restant',
            'revenu',  # ✅ Champ ajouté
        ]

    def get_statut(self, paiement):
        total_attendu = paiement.AchatsID.ProduitID.Produit_prix * paiement.AchatsID.Achat_quantite
        total_deja_paye = paiement.AchatsID.paiements_details.aggregate(
            total=Sum('Paiement_montant')
        )['total'] or Decimal('0')
        return 'complet' if total_deja_paye >= total_attendu else 'incomplet'

    def get_reste_a_payer(self, paiement):
        total_attendu = paiement.AchatsID.ProduitID.Produit_prix * paiement.AchatsID.Achat_quantite
        total_deja_paye = paiement.AchatsID.paiements_details.aggregate(
            total=Sum('Paiement_montant')
        )['total'] or Decimal('0')
        reste = max(total_attendu - total_deja_paye, Decimal('0'))
        return float(round(reste, 2))

    def get_nombredemois_restant(self, paiement):
        total_attendu = paiement.AchatsID.ProduitID.Produit_prix * paiement.AchatsID.Achat_quantite
        total_deja_paye = paiement.AchatsID.paiements_details.aggregate(
            total=Sum('Paiement_montant')
        )['total'] or Decimal('0')

        montant_choisi = paiement.Paiement_montantchoisi
        if not montant_choisi or montant_choisi == 0:
            return None

        reste = max(total_attendu - total_deja_paye, Decimal('0'))
        nombredemois = int(reste / montant_choisi) if montant_choisi else None
        return nombredemois

    def get_revenu(self, paiement):
        total_attendu = paiement.AchatsID.ProduitID.Produit_prix * paiement.AchatsID.Achat_quantite
        total_deja_paye = paiement.AchatsID.paiements_details.aggregate(
            total=Sum('Paiement_montant')
        )['total'] or Decimal('0')
        revenu = max(total_deja_paye - total_attendu, Decimal('0'))
        return float(round(revenu, 2)) if revenu > 0 else 0
