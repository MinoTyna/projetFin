from django.shortcuts import render

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics
from rest_framework import status
from .models import Gestion
from .serializers import GestionSerializer

class GestionCreateView(generics.CreateAPIView):
    queryset = Gestion.objects.all()
    serializer_class = GestionSerializer

    def perform_create(self, serializer):
        gestion = serializer.save()
        produit = gestion.ProduitID
        produit.Produit_quantite = (produit.Produit_quantite or 0) + gestion.Gestion_quantite
        produit.save()


class GestionListView(generics.ListAPIView):
    queryset = Gestion.objects.all().order_by('-Gestion_date')
    serializer_class = GestionSerializer

class GestiontDeleteAPIView(APIView):
    def delete(self, request, gestion_id):
        try:
            Gestion = Gestion.objects.get(id=gestion_id)
        except Gestion.DoesNotExist:
            return Response({"error": "Gestion introuvable."}, status=status.HTTP_404_NOT_FOUND)

        produit = Gestion.ProduitID
        # Décrémenter le stock du produit
        produit.Produit_quantite = max((produit.Produit_quantite or 0) - Gestion.Gestion_quantite, 0)  
        produit.save()

        # Supprimer l'insertion
        Gestion.delete()

        return Response({"message": "Gestion supprimé avec succès et stock mis à jour."}, status=status.HTTP_200_OK)