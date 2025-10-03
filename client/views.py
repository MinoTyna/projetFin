from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404
from .models import Client
from .serializers import ClientSerializer
from django.conf import settings
# monbackend/views.py
import requests


# ðŸ”¹ GET : Liste des clients
class ClientListAPIView(APIView):
    def get(self, request):
        clients = Client.objects.all()
        serializer = ClientSerializer(clients, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

# ðŸ”¹ GET : Total des clients
class ClientTotalAPIView(APIView):
    def get(self, request):
        total_clients = Client.objects.count()
        return Response({"total_clients": total_clients}, status=status.HTTP_200_OK)

class ClientDetailAPIView(APIView):
    def get_object(self, id):
        try:
            return Client.objects.get(id=id)
        except Client.DoesNotExist:
            raise Http404

    def get(self, request, id):
        client = self.get_object(id)
        serializer = ClientSerializer(client)
        return Response(serializer.data, status=status.HTTP_200_OK)


from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import make_password
from .models import Client
from .serializers import ClientSerializer

class ClientCreateAPIView(APIView):
    def post(self, request):
        cin = request.data.get('Client_cin')
        if Client.objects.filter(Client_cin=cin).exists():
            return Response({"error": "Le client avec ce CIN existe déjà."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ClientSerializer(data=request.data)
        if serializer.is_valid():
            client = serializer.save()

            # Hasher le mot de passe avant sauvegarde
            raw_password = request.data.get("password")
            if raw_password:
                client.password = make_password(raw_password)
                client.save()

            # Générer le token
            refresh = RefreshToken.for_user(client)
            token = str(refresh.access_token)

            return Response({
                "token": token,
                "user": {
                    "id": client.id,
                    "Client_role": client.Client_role,
                    "Client_nom": client.Client_nom,
                    "Client_prenom": client.Client_prenom,
                }
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        
# ðŸ”¹ DELETE : Supprimer un client par son id
class ClientDeleteAPIView(APIView):
    def delete(self, request, client_id):
        try:
            client = Client.objects.get(id=client_id)
        except Client.DoesNotExist:
            return Response({"error": "Client introuvable."}, status=status.HTTP_404_NOT_FOUND)

        client.delete()
        return Response({"message": "Client supprimÃ© avec succÃ¨s."}, status=status.HTTP_200_OK)

# class ClientUpdateAPIView(APIView):
#     def put(self, request, client_id):
#         try:
#             client = Client.objects.get(id=client_id)
#         except Client.DoesNotExist:
#             return Response({"error": "client introuvable."}, status=status.HTTP_404_NOT_FOUND)

#         serializer = ClientSerializer(client, data=request.data, partial=True)  # partial=True pour update partiel
#         if serializer.is_valid():
#             serializer.save()
#             return Response({"message": "Client mis Ã  jour avec succÃ¨s.", "client": serializer.data}, status=status.HTTP_200_OK)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ClientUpdateAPIView(APIView):
    def put(self, request, pk):
        try:
            client = Client.objects.get(pk=pk)

            # Récupération des champs
            nom = request.data.get("Client_nom")
            prenom = request.data.get("Client_prenom")
            cin = request.data.get("Client_cin")
            telephone1 = request.data.get("Client_telephone1")
            telephone2 = request.data.get("Client_telephone2")
            telephone3 = request.data.get("Client_telephone3")
            telephone4 = request.data.get("Client_telephone4")
            adresse = request.data.get("Client_adresse")
            latitude = request.data.get("latitude")
            longitude = request.data.get("longitude")

            # Mise à jour des champs
            if nom: client.Client_nom = nom
            if prenom: client.Client_prenom = prenom
            if cin: client.Client_cin = cin
            if telephone1 is not None: client.Client_telephone1 = telephone1
            if telephone2 is not None: client.Client_telephone2 = telephone2
            if telephone3 is not None: client.Client_telephone3 = telephone3
            if telephone4 is not None: client.Client_telephone4 = telephone4
            if adresse: client.Client_adresse = adresse

            if latitude: client.latitude = float(latitude)
            if longitude: client.longitude = float(longitude)

            # Mise à jour de la photo si présente
            if "Client_photo" in request.FILES:
                client.Client_photo = request.FILES["Client_photo"]

            client.save()
            return Response({"message": "Client mis à jour"}, status=status.HTTP_200_OK)

        except Client.DoesNotExist:
            return Response({"error": "Client non trouvé"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GeocodeAPIView(APIView):
    def get(self, request):
        address = request.GET.get('address')
        if not address:
            return Response({"error": "Adresse non fournie"}, status=status.HTTP_400_BAD_REQUEST)

        api_key = settings.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={api_key}"

        response = requests.get(url)
        data = response.json()

        if data.get("status") != "OK":
            return Response({"error": data.get("error_message", "Adresse introuvable")}, status=400)

        location = data["results"][0]["geometry"]["location"]
        return Response(location, status=200)
        

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.hashers import check_password
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Client
from .serializers import ClientSerializer


class ConnexionClientAPIView(APIView):
    def post(self, request):
        data = request.data
        email = data.get("Client_email")
        nom = data.get("Client_nom")
        prenom = data.get("Client_prenom", None)
        password = data.get("password")

        if not password:
            return Response({"error": "Mot de passe requis"}, status=400)

        try:
            # Connexion par email
            if email:
                client = Client.objects.get(Client_email=email)

            # Connexion par nom (+ éventuellement prénom)
            elif nom:
                if prenom:
                    try:
                        client = Client.objects.get(Client_nom=nom, Client_prenom=prenom)
                    except Client.DoesNotExist:
                        return Response({"error": "Nom + prénom incorrects"}, status=400)
                else:
                    clients = Client.objects.filter(Client_nom=nom)
                    if clients.count() > 1:
                        return Response(
                            {"error": "Plusieurs clients ont ce nom, entrez aussi votre prénom"},
                            status=400
                        )
                    elif clients.exists():
                        client = clients.first()
                    else:
                        return Response({"error": "Client non trouvé"}, status=400)

            else:
                return Response({"error": "Email ou Nom requis"}, status=400)

            # Vérification du mot de passe hashé
            if not check_password(password, client.password):
                return Response({"error": "Mot de passe incorrect"}, status=400)

            # Génération du JWT
            refresh = RefreshToken.for_user(client)
            refresh["email"] = client.Client_email
            refresh["nom"] = client.Client_nom
            refresh["prenom"] = client.Client_prenom if client.Client_prenom else ""
            refresh["role"] = client.Client_role

            access_token = str(refresh.access_token)
            serializer = ClientSerializer(client)

            # Réponse avec cookie HTTP-only + token dans le body
            response = Response({
                "user": serializer.data,
                "message": "Connexion réussie",
                "token": access_token
            }, status=status.HTTP_200_OK)

            response.set_cookie(
                key="token",
                value=access_token,
                httponly=True,
                secure=True,      # False en dev si pas HTTPS
                samesite="None",  # nécessaire si cross-domain
                max_age=60*60*24*7,  # 7 jours
                path="/"
            )

            return response

        except Client.DoesNotExist:
            return Response({"error": "Client non trouvé"}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
