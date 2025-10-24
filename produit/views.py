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
    parser_classes = [MultiPartParser, FormParser]  # ⚡ important pour les fichiers

    def post(self, request):
        serializer = ProduitSerializer(data=request.data)
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

class ProduitUpdateAPIView(APIView):
    def put(self, request, produit_id):
        try:
            produit = Produit.objects.get(id=produit_id)
        except Produit.DoesNotExist:
            return Response({"error": "Produit introuvable."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProduitSerializer(produit, data=request.data, partial=True)  # partial=True pour update partiel
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Produit mis Ã  jour avec succÃ¨s.", "produit": serializer.data}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
