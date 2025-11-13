from rest_framework import serializers
from .models import Responsable
from supabase import create_client
import time

# Supabase config
SUPABASE_URL = "https://rcbhcqyypiaatvcyolnw.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJjYmhjcXl5cGlhYXR2Y3lvbG53Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MTMyNDg3NiwiZXhwIjoyMDc2OTAwODc2fQ.gYH7mU0brZZ7bRF-1uo0QdLJcY45M9nYeBt0fzW2vlc"
BUCKET = "media"
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

class ResponsableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Responsable
        fields = '__all__'

    def create(self, validated_data):
        request = self.context.get('request')
        uploaded_file = None
        if request and hasattr(request, "FILES"):
            uploaded_file = request.FILES.get('Responsable_photo')

        # Créer le responsable sans photo pour l’instant
        responsable = Responsable.objects.create(**validated_data)

        if uploaded_file:
            # Nom unique du fichier
            filename = f"{int(time.time())}_{uploaded_file.name}"

            # Upload sur Supabase
            supabase.storage.from_(BUCKET).upload(
                filename,
                uploaded_file.read(),
                {"content-type": uploaded_file.content_type}
            )

            # Stocker juste le nom du fichier dans le modèle
            responsable.Responsable_photo = filename
            responsable.save()

        return responsable

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        
        if instance.Responsable_photo:
            # ⚡ Récupérer le nom du fichier depuis ImageField
            filename = instance.Responsable_photo.name  # c’est une str
            
            # URL locale Django
            rep["Responsable_photo"] = instance.Responsable_photo.url  # http://localhost:8000/media/xxx.png
            
            # URL publique Supabase
            rep["Responsable_photo_url"] = f"https://rcbhcqyypiaatvcyolnw.supabase.co/storage/v1/object/public/media/{filename}"
        else:
            rep["Responsable_photo"] = None
            rep["Responsable_photo_url"] = None

        return rep

