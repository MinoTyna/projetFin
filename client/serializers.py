# from rest_framework import serializers
# from .models import Client
# from supabase import create_client
# import time

# # Supabase config directe
# SUPABASE_URL = "https://rcbhcqyypiaatvcyolnw.supabase.co"
# SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJjYmhjcXl5cGlhYXR2Y3lvbG53Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MTMyNDg3NiwiZXhwIjoyMDc2OTAwODc2fQ.gYH7mU0brZZ7bRF-1uo0QdLJcY45M9nYeBt0fzW2vlc"
# BUCKET = "media"

# supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
# class ClientSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Client
#         fields = '__all__'
from rest_framework import serializers
from .models import Client
from supabase import create_client
import time, re, unicodedata

# Supabase config
SUPABASE_URL = "https://rcbhcqyypiaatvcyolnw.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJjYmhjcXl5cGlhYXR2Y3lvbG53Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MTMyNDg3NiwiZXhwIjoyMDc2OTAwODc2fQ.gYH7mU0brZZ7bRF-1uo0QdLJcY45M9nYeBt0fzW2vlc"
BUCKET = "media"

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

   
class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = '__all__'

    def create(self, validated_data):
        uploaded_file = self.context['request'].FILES.get('Client_photo')

        if uploaded_file:
            # Nom unique pour Supabase
            filename = f"{int(time.time())}_{uploaded_file.name}"

            # Upload vers Supabase
            supabase.storage.from_(BUCKET).upload(
                filename,
                uploaded_file.read(),
                {"content-type": uploaded_file.content_type}
            )

            # Stocker le fichier dans Django MEDIA_ROOT via ImageField
            validated_data['Client_photo'] = uploaded_file

        # Créer l'objet Client (pas de Client_photo_name !)
        client = Client.objects.create(**validated_data)
        return client

    def to_representation(self, instance):
        rep = super().to_representation(instance)

        if instance.Client_photo:
            # URL locale Django
            rep["Client_photo"] = instance.Client_photo.url
            # URL publique Supabase
            rep["Client_photo_url"] = f"https://rcbhcqyypiaatvcyolnw.supabase.co/storage/v1/object/public/media/{instance.Client_photo.name.split('/')[-1]}"
        else:
            rep["Client_photo"] = None
            rep["Client_photo_url"] = None

        return rep

