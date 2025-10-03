from rest_framework import serializers
from .models import Gestion

class GestionSerializer(serializers.ModelSerializer):
    Responsable_nom = serializers.CharField(source='responsable.Responsable_email', read_only=True)
    Produit_nom = serializers.CharField(source='produit.Produit_nom', read_only=True)

    class Meta:
        model = Gestion
        fields = ['id', 'ResponsableID', 'Responsable_nom', 'ProduitID', 'Produit_nom', 'Gestion_date', 'Gestion_quantite']
