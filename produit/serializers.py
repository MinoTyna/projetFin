from rest_framework import serializers
from .models import Produit
from responsable.models import Responsable
from supabase import create_client
import re

# Supabase config
SUPABASE_URL = "https://rcbhcqyypiaatvcyolnw.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJjYmhjcXl5cGlhYXR2Y3lvbG53Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MTMyNDg3NiwiZXhwIjoyMDc2OTAwODc2fQ.gYH7mU0brZZ7bRF-1uo0QdLJcY45M9nYeBt0fzW2vlc"
BUCKET = "media"

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ------------------ Utils ------------------
def safe_filename(name: str) -> str:
    """Remplacer les caractères spéciaux par _ pour éviter les erreurs."""
    name = name.strip()
    name = re.sub(r'[^A-Za-z0-9_.-]', '_', name)
    return name

# ------------------ Responsable Nested Serializer ------------------
class ResponsableNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Responsable
        fields = ['id', 'Responsable_nom', 'Responsable_prenom', 'Responsable_email']

# ------------------ Produit Serializer ------------------
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

 # ---------------- CREATE ----------------
    def create(self, validated_data):
        responsable = validated_data.pop('responsable_id', None)
        uploaded_file = self.context['request'].FILES.get('Produit_photo')

        if uploaded_file:
            filename = safe_filename(uploaded_file.name)
            ext = filename.split('.')[-1].lower()

            # Déterminer le content-type
            if ext == 'png':
                content_type = 'image/png'
            elif ext in ['jpg', 'jpeg']:
                content_type = 'image/jpeg'
            else:
                content_type = uploaded_file.content_type  # fallback

            # Supprimer ancien fichier si existe
            try:
                supabase.storage.from_(BUCKET).remove([filename])
            except Exception:
                pass

            # Upload
            supabase.storage.from_(BUCKET).upload(
                filename,
                uploaded_file.read(),
                {"content-type": content_type}
            )

            validated_data['Produit_photo'] = filename

        produit = Produit.objects.create(**validated_data)
        if responsable:
            produit.responsable = responsable
            produit.save()
        return produit


    # ---------------- UPDATE ----------------
    def update(self, instance, validated_data):
        responsable = validated_data.pop('responsable_id', None)
        if responsable:
            instance.responsable = responsable

        uploaded_file = self.context['request'].FILES.get('Produit_photo')
        if uploaded_file:
            filename = safe_filename(uploaded_file.name)
            ext = filename.split('.')[-1].lower()

            if ext == 'png':
                content_type = 'image/png'
            elif ext in ['jpg', 'jpeg']:
                content_type = 'image/jpeg'
            else:
                content_type = uploaded_file.content_type

            # Supprimer l’ancien fichier si existe
            try:
                supabase.storage.from_(BUCKET).remove([filename])
            except Exception:
                pass

            supabase.storage.from_(BUCKET).upload(
                filename,
                uploaded_file.read(),
                {"content-type": content_type}
            )

            instance.Produit_photo = filename

        # Mettre à jour les autres champs
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance

    # ---------------- REPRESENTATION ----------------
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.Produit_photo:
            # URL locale Django
            rep["Produit_photo"] = f"/media/{instance.Produit_photo}"
            # URL publique Supabase
            rep["Produit_photo_url"] = f"https://rcbhcqyypiaatvcyolnw.supabase.co/storage/v1/object/public/media/{instance.Produit_photo}"
        else:
            rep["Produit_photo"] = None
            rep["Produit_photo_url"] = None
        return rep
