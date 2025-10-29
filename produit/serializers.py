# from rest_framework import serializers
# from .models import Produit
# from responsable.models import Responsable
# from supabase import create_client
# import time

# # Supabase config directe
# SUPABASE_URL = "https://rcbhcqyypiaatvcyolnw.supabase.co"
# SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJjYmhjcXl5cGlhYXR2Y3lvbG53Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MTMyNDg3NiwiZXhwIjoyMDc2OTAwODc2fQ.gYH7mU0brZZ7bRF-1uo0QdLJcY45M9nYeBt0fzW2vlc"
# BUCKET = "media"

# supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# # Serializer imbriqué pour Responsable
# class ResponsableNestedSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Responsable
#         fields = ['id', 'Responsable_nom', 'Responsable_prenom', 'Responsable_email']

# # Serializer principal pour Produit
# class ProduitSerializer(serializers.ModelSerializer):
#     responsable = ResponsableNestedSerializer(read_only=True)
#     responsable_id = serializers.PrimaryKeyRelatedField(
#         queryset=Responsable.objects.all(),
#         write_only=True,
#         required=False
#     )

#     class Meta:
#         model = Produit
#         fields = [
#             'id',
#             'Produit_nom',
#             'Produit_description',
#             'Produit_reference',
#             'Produit_prix',
#             'Produit_photo',
#             'Produit_quantite',
#             'Produit_categorie',
#             'date',
#             'responsable',
#             'responsable_id',
#         ]

#     def create(self, validated_data):
#         responsable = validated_data.pop('responsable_id', None)

#         # ⚡ Upload de l'image sur Supabase si fournie
#         uploaded_file = self.context['request'].FILES.get('Produit_photo')
#         if uploaded_file:
#             filename = f"{int(time.time())}_{uploaded_file.name}"
#             supabase.storage.from_(BUCKET).upload(
#                 filename,
#                 uploaded_file.read(),  # ⚡ convertir en bytes
#                 {"content-type": uploaded_file.content_type}
#             )
#             validated_data['Produit_photo'] = filename


#         produit = Produit.objects.create(**validated_data)
#         if responsable:
#             produit.responsable = responsable
#             produit.save()
#         return produit

#     def to_representation(self, instance):
#         rep = super().to_representation(instance)
#         if instance.Produit_photo:
#             # SDK retourne directement l'URL publique
#             url = supabase.storage.from_(BUCKET).get_public_url(instance.Produit_photo)
#             rep['Produit_photo_url'] = url
#         return rep
from rest_framework import serializers
from .models import Produit
from responsable.models import Responsable
from supabase import create_client
import time

# Supabase config directe
SUPABASE_URL = "https://rcbhcqyypiaatvcyolnw.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJjYmhjcXl5cGlhYXR2Y3lvbG53Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MTMyNDg3NiwiZXhwIjoyMDc2OTAwODc2fQ.gYH7mU0brZZ7bRF-1uo0QdLJcY45M9nYeBt0fzW2vlc"
BUCKET = "media"

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

class ResponsableNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Responsable
        fields = ['id', 'Responsable_nom', 'Responsable_prenom', 'Responsable_email']

class ProduitSerializer(serializers.ModelSerializer):
    responsable = ResponsableNestedSerializer(read_only=True)
    responsable_id = serializers.PrimaryKeyRelatedField(
        queryset=Responsable.objects.all(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Produit
        fields = [
            'id',
            'Produit_nom',
            'Produit_description',
            'Produit_reference',
            'Produit_prix',
            'Produit_photo',
            'Produit_quantite',
            'Produit_categorie',
            'date',
            'responsable',
            'responsable_id',
        ]

    
    def create(self, validated_data):
        responsable = validated_data.pop('responsable_id', None)
        uploaded_file = self.context['request'].FILES.get('Produit_photo')

        if uploaded_file:
            # Nom unique du fichier pour Supabase
            filename = f"{int(time.time())}_{uploaded_file.name}"
            supabase.storage.from_(BUCKET).upload(
                filename,
                uploaded_file.read(),
                {"content-type": uploaded_file.content_type}
            )
            # Stocker uniquement le nom du fichier dans la DB
            validated_data['Produit_photo'] = filename

        produit = Produit.objects.create(**validated_data)
        if responsable:
            produit.responsable = responsable
            produit.save()

        return produit

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        
        if instance.Produit_photo:
            # ⚡ Récupérer le nom du fichier depuis ImageField
            filename = instance.Produit_photo.name  # c’est une str
            
            # URL locale Django
            rep["Produit_photo"] = instance.Produit_photo.url  # http://localhost:8000/media/xxx.png
            
            # URL publique Supabase
            rep["Produit_photo_url"] = f"https://rcbhcqyypiaatvcyolnw.supabase.co/storage/v1/object/public/media/{filename}"
        else:
            rep["Produit_photo"] = None
            rep["Produit_photo_url"] = None

        return rep

