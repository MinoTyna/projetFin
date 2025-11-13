from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Produit
from .serializers import ProduitSerializer
from django.db.models import Sum
# ðŸ”¹ GET : Liste des Produits
class ProduitListAPIView(APIView):
    def get(self, request):
        Produits = Produit.objects.all()
        serializer = ProduitSerializer(Produits, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

# ðŸ”¹ GET : Total des Produits
class ProduitTotalAPIView(APIView):
    def get(self, request):
        total_quantite = Produit.objects.aggregate(total=Sum("Produit_quantite"))["total"] or 0
        return Response({"total_Produits": total_quantite}, status=status.HTTP_200_OK)



# ðŸ”¹ POST : CrÃ©er un nouveau Produit
# class ProduitCreateAPIView(APIView):
#     def post(self, request):
#         serializer = ProduitSerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import ProduitSerializer

class ProduitCreateAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = ProduitSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProduitDeleteAPIView(APIView):
    def delete(self, request, produit_id):
        try:
            produit = Produit.objects.get(id=produit_id)
        except Produit.DoesNotExist:
            return Response({"error": "Produit introuvable."}, status=status.HTTP_404_NOT_FOUND)

        produit.delete()
        return Response({"message": "Produit supprimÃ© avec succÃ¨s."}, status=status.HTTP_200_OK)


from supabase import create_client
import time

# Supabase config
SUPABASE_URL = "https://rcbhcqyypiaatvcyolnw.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJjYmhjcXl5cGlhYXR2Y3lvbG53Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MTMyNDg3NiwiZXhwIjoyMDc2OTAwODc2fQ.gYH7mU0brZZ7bRF-1uo0QdLJcY45M9nYeBt0fzW2vlc"
BUCKET = "media"
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

class ProduitUpdateAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def patch(self, request, produit_id):  # PATCH au lieu de PUT
        try:
            produit = Produit.objects.get(id=produit_id)
        except Produit.DoesNotExist:
            return Response({"error": "Produit introuvable."}, status=404)

        serializer = ProduitSerializer(
            produit,
            data=request.data,
            partial=True,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Produit mis à jour avec succès", "produit": serializer.data}, status=200)

        return Response(serializer.errors, status=400)
