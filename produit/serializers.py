from rest_framework import serializers
from .models import Produit
from responsable.models import Responsable  # ← assure-toi que c’est bien importé

# ✅ Définis d'abord le serializer imbriqué pour Responsable
class ResponsableNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Responsable
        fields = ['id', 'Responcable_nom', 'Responcable_prenom', 'Responcable_email']

# ✅ Ensuite, utilise-le dans le serializer du produit
class ProduitSerializer(serializers.ModelSerializer):
    responsable = ResponsableNestedSerializer(read_only=True)
    Produit_photo = serializers.ImageField(use_url=True)  # ⚡ renvoie l'URL complète

    class Meta:
        model = Produit
        fields = '__all__'
