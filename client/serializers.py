from rest_framework import serializers
from .models import Client
from supabase import create_client
import re, time

# --- Supabase config ---
SUPABASE_URL = "https://rcbhcqyypiaatvcyolnw.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJjYmhjcXl5cGlhYXR2Y3lvbG53Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MTMyNDg3NiwiZXhwIjoyMDc2OTAwODc2fQ.gYH7mU0brZZ7bRF-1uo0QdLJcY45M9nYeBt0fzW2vlc"
BUCKET = "media"

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# --- Utilitaire pour nettoyer le nom du fichier ---
def safe_filename(name: str) -> str:
    name = name.strip()
    name = re.sub(r'[^A-Za-z0-9_.-]', '_', name)
    timestamp = int(time.time())
    return f"{timestamp}_{name}"


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = "__all__"

    # ---------------- CREATE ----------------
    def create(self, validated_data):
        uploaded_file = self.context["request"].FILES.get("Client_photo")

        if uploaded_file:
            filename = safe_filename(uploaded_file.name)
            ext = filename.split(".")[-1].lower()

            # Type MIME
            if ext == "png":
                content_type = "image/png"
            elif ext in ["jpg", "jpeg"]:
                content_type = "image/jpeg"
            else:
                content_type = uploaded_file.content_type

            try:
                supabase.storage.from_(BUCKET).upload(
                    filename,
                    uploaded_file.read(),
                    {"content-type": content_type},
                )
                validated_data["Client_photo"] = filename
            except Exception as e:
                raise serializers.ValidationError(
                    {"Client_photo": f"Erreur d’upload vers Supabase : {str(e)}"}
                )

        client = Client.objects.create(**validated_data)
        return client

    # ---------------- UPDATE ----------------
    def update(self, instance, validated_data):
        uploaded_file = self.context["request"].FILES.get("Client_photo")

        if uploaded_file:
            filename = safe_filename(uploaded_file.name)
            ext = filename.split(".")[-1].lower()

            if ext == "png":
                content_type = "image/png"
            elif ext in ["jpg", "jpeg"]:
                content_type = "image/jpeg"
            else:
                content_type = uploaded_file.content_type

            # Supprimer l’ancienne image sur Supabase
            try:
                if instance.Client_photo:
                    supabase.storage.from_(BUCKET).remove([instance.Client_photo])
            except Exception:
                pass

            # Upload nouvelle image
            try:
                supabase.storage.from_(BUCKET).upload(
                    filename,
                    uploaded_file.read(),
                    {"content-type": content_type},
                )
                instance.Client_photo = filename
            except Exception as e:
                raise serializers.ValidationError(
                    {"Client_photo": f"Erreur d’upload Supabase : {str(e)}"}
                )

        # Mettre à jour les autres champs
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance

    # ---------------- REPRESENTATION ----------------
    def to_representation(self, instance):
        rep = super().to_representation(instance)

        if instance.Client_photo:
            rep["Client_photo"] = f"/media/{instance.Client_photo}"
            rep["Client_photo_url"] = (
                f"https://rcbhcqyypiaatvcyolnw.supabase.co/storage/v1/object/public/media/{instance.Client_photo}"
            )
        else:
            rep["Client_photo"] = None
            rep["Client_photo_url"] = None

        return rep
