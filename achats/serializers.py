from rest_framework import serializers
from .models import Achat
from .models import Facture
from .models import Notification, NotificationProduit

class AchatReadSerializer(serializers.ModelSerializer):
    client = serializers.CharField(source='ClientID.Client_nom', read_only=True)
    responsable = serializers.CharField(source='ResponsableID.Responsable_email', read_only=True)
    produit = serializers.CharField(source='ProduitID.Produit_nom', read_only=True)
    photo = serializers.SerializerMethodField()
    stock = serializers.SerializerMethodField()
    quantite = serializers.IntegerField(source='Achat_quantite', read_only=True)
    prix_unitaire = serializers.SerializerMethodField()
    prix_total = serializers.SerializerMethodField()
    date = serializers.DateTimeField(source='Achat_date', format="%d-%m-%Y %H:%M", read_only=True)

    class Meta:
        model = Achat
        fields = [
            'id',
            'client',
            'responsable',
            'produit',
            'photo',
            'stock',
            'quantite',
            'date',
            'prix_unitaire',
            'prix_total',
        ]

    def get_prix_unitaire(self, obj):
        return obj.ProduitID.Produit_prix

    def get_prix_total(self, obj):
        return obj.ProduitID.Produit_prix * obj.Achat_quantite

    def get_photo(self, obj):
        request = self.context.get('request')
        photo = obj.ProduitID.Produit_photo
        if photo and hasattr(photo, 'url'):
            return request.build_absolute_uri(photo.url) if request else photo.url
        return None

    def get_stock(self, obj):
        return obj.ProduitID.Produit_quantite




class NotificationProduitSerializer(serializers.ModelSerializer):
    nom = serializers.CharField(source='produit.Produit_nom', read_only=True)
    prix = serializers.FloatField(source='produit.Produit_prix', read_only=True)
    photo = serializers.SerializerMethodField()

    class Meta:
        model = NotificationProduit
        fields = ['id', 'nom', 'prix', 'photo', 'quantite']

    def get_photo(self, obj):
        if obj.produit.Produit_photo:
            return obj.produit.Produit_photo.url
        return None


class NotificationSerializer(serializers.ModelSerializer):
    vue = serializers.BooleanField(read_only=True)
    vue_client = serializers.BooleanField(read_only=True)
    client_nom = serializers.CharField(source='client.Client_nom', read_only=True)
    client_prenom = serializers.CharField(source='client.Client_prenom', read_only=True)
    produit_nom = serializers.CharField(source='produit.Produit_nom', read_only=True)
    url = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id', 'client_id', 'client_nom', 'client_prenom',
            'mode_reception', 'produit_nom', 'message',
            'vue', 'vue_client', 'created_at', 'url'
        ]




class AchatWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Achat
        fields = ['ClientID', 'ResponsableID', 'ProduitID', 'Achat_quantite']

class FactureCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Facture
        fields = ['achat'] 