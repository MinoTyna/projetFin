from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Responsable
from .serializers import ResponsableSerializer

# class SyncResponsableAPIView(APIView):
#     def post(self, request):
#         data = request.data
#         Responsable_email = data.get("Responsable_email")
#         if not Responsable_email:
#             return Response({"error": "Email requis"}, status=400)

#         responsable, created = Responsable.objects.update_or_create(
#             Responsable_email=Responsable_email,
#             defaults={
#                 'Responsable_nom': data.get('Responsable_nom'),  # None autorisé
#                 'Responsable_prenom': data.get('Responsable_prenom'),
#                 'Responsable_adresse': data.get('Responsable_adresse'),
#                 'Responsable_telephone': data.get('Responsable_telephone'),
#                 'Responsable_role': data.get('Responsable_role', 'vendeur'),
#             }
#         )
#         serializer = ResponsableSerializer(responsable)
#         return Response(serializer.data, status=status.HTTP_200_OK)




from django.contrib.auth.hashers import make_password,check_password

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.hashers import make_password,check_password
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Responsable
from .serializers import ResponsableSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Responsable
from .serializers import ResponsableSerializer

class SyncResponsableAPIView(APIView):
    permission_classes = [AllowAny]  # Permet d’accéder sans token (important pour signup)

    def post(self, request):
        data = request.data
        email = data.get("Responsable_email")

        if not email:
            return Response({"error": "Email requis"}, status=status.HTTP_400_BAD_REQUEST)

        update_fields = {
            'Responsable_nom': data.get('Responsable_nom'),
            'Responsable_prenom': data.get('Responsable_prenom'),
            'Responsable_adresse': data.get('Responsable_adresse'),
            'Responsable_telephone': data.get('Responsable_telephone'),
            'Responsable_role': data.get('Responsable_role', 'vendeur'),
        }

        mot_de_passe = data.get("password")
        if mot_de_passe:
            update_fields["password"] = make_password(mot_de_passe)
        else:
            return Response({"error": "Mot de passe requis"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            responsable, created = Responsable.objects.update_or_create(
                Responsable_email=email,
                defaults=update_fields
            )
        except Exception as e:
            return Response({"error": "Erreur serveur interne", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        refresh = RefreshToken.for_user(responsable)
        refresh['email'] = responsable.Responsable_email
        refresh['nom'] = responsable.Responsable_nom
        refresh['role'] = responsable.Responsable_role
        refresh['photo'] = responsable.Responsable_photo or ""

        access_token = str(refresh.access_token)

        serializer = ResponsableSerializer(responsable)

        return Response({
            "user": serializer.data,
            "token": access_token,
        }, status=status.HTTP_200_OK)



# class ConnexionResponsableAPIView(APIView):
#     def post(self, request):
#         data = request.data
#         email = data.get("Responsable_email")
#         password = data.get("password")

#         try:
#             responsable = Responsable.objects.get(Responsable_email=email)

#             if not check_password(password, responsable.password):
#                 return Response({"error": "Mot de passe incorrect"}, status=400)

#             refresh = RefreshToken.for_user(responsable)
#             # ✅ Ajouter les claims avec string uniquement
#             refresh['email'] = responsable.Responsable_email
#             refresh['nom'] = responsable.Responsable_nom
#             refresh['role'] = responsable.Responsable_role
#             refresh['photo'] = responsable.Responsable_photo.url if responsable.Responsable_photo else ""

#             access_token = str(refresh.access_token)

#             serializer = ResponsableSerializer(responsable)
#             return Response({
#                 "user": serializer.data,
#                 "token": access_token,
#             }, status=status.HTTP_200_OK)

#         except Responsable.DoesNotExist:
#             return Response({"error": "Email non trouvé"}, status=400)


from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password
from .models import Responsable
from .serializers import ResponsableSerializer

class ConnexionResponsableAPIView(APIView):
    def post(self, request):
        data = request.data
        email = data.get("Responsable_email")
        password = data.get("password")

        try:
            responsable = Responsable.objects.get(Responsable_email=email)

            if not check_password(password, responsable.password):
                return Response({"error": "Mot de passe incorrect"}, status=400)

            # Génération du JWT
            refresh = RefreshToken.for_user(responsable)
            refresh["email"] = responsable.Responsable_email
            refresh["nom"] = responsable.Responsable_nom
            refresh["role"] = responsable.Responsable_role
            refresh["photo"] = responsable.Responsable_photo.url if responsable.Responsable_photo else ""

            access_token = str(refresh.access_token)

            serializer = ResponsableSerializer(responsable)

            # Création de la réponse avec cookie HTTP-only
            response = Response({
            "user": serializer.data,
            "message": "Connexion réussie",
            "token": access_token  # ✅ envoyé aussi dans le body pour localStorage
               }, status=status.HTTP_200_OK)


            response.set_cookie(
            key="token",
            value=access_token,
            httponly=True,        # cookie non accessible par JS
            secure=True,          # obligatoire si HTTPS
            samesite="None",      # nécessaire pour cross-domain
            max_age=60 * 60 * 24 * 7,  # 7 jours
            path="/",
        )


            return response

        except Responsable.DoesNotExist:
            return Response({"error": "Email non trouvé"}, status=400)

class LogoutAPIView(APIView):
    def post(self, request):
        response = Response({"message": "Déconnexion réussie"})
        response.delete_cookie("token")
        return response


class ResponsableTotalAPIView(APIView):
    def get(self, request):
        total_Responsables = Responsable.objects.count()
        return Response({"total_Responsables": total_Responsables}, status=status.HTTP_200_OK)



class ResponsableListAPIView(APIView):
    def get(self, request):
        Responsable_email = request.GET.get('Responsable_email')
        if Responsable_email:
            try:
                responsable = Responsable.objects.get(Responsable_email=Responsable_email)
                serializer = ResponsableSerializer(responsable)
                return Response(serializer.data)
            except Responsable.DoesNotExist:
                return Response({"detail": "Responsable non trouvé"}, status=status.HTTP_404_NOT_FOUND)
        else:
            responsables = Responsable.objects.all()
            serializer = ResponsableSerializer(responsables, many=True)
            return Response(serializer.data)
        
        
class ResponsabletUpdateAPIView(APIView):
    def put(self, request, responsable_id):
        try:
            responsable = Responsable.objects.get(id=responsable_id)
        except Responsable.DoesNotExist:
            return Response({"error": "responsable introuvable."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ResponsableSerializer(responsable, data=request.data, partial=True)  # partial=True pour update partiel
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "responsable mis à jour avec succès.", "responsable": serializer.data}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResponsableDetailView(APIView):
    def get(self, request, pk):
        try:
            responsable = Responsable.objects.get(pk=pk)
            serializer = ResponsableSerializer(responsable)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Responsable.DoesNotExist:
            return Response(
                {"detail": "Responsable non trouvé."},
                status=status.HTTP_404_NOT_FOUND
            )
        


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth.hashers import make_password
from .models import Responsable


class PasswordResetRequestAPIView(APIView):
    def post(self, request):
        email = request.data.get("Responsable_email")
        if not email:
            return Response({"error": "Email requis"}, status=400)

        try:
            responsable = Responsable.objects.get(Responsable_email=email)
            uid = urlsafe_base64_encode(force_bytes(responsable.pk))
            token = PasswordResetTokenGenerator().make_token(responsable)

            reset_url = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"

            send_mail(
                subject="Réinitialisation de mot de passe",
                message=f"Bonjour {responsable.Responsable_nom},\n\nPour réinitialiser votre mot de passe, cliquez sur ce lien : {reset_url}\n\nSi vous n'avez pas demandé cette réinitialisation, ignorez cet email.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )

            return Response({"message": "Lien de réinitialisation envoyé par email"}, status=200)
        except Responsable.DoesNotExist:
            return Response({"error": "Aucun utilisateur trouvé avec cet email"}, status=404)



class PasswordResetConfirmAPIView(APIView):
    def post(self, request):
        uidb64 = request.data.get("uid")
        token = request.data.get("token")
        new_password = request.data.get("new_password")

        if not uidb64 or not token or not new_password:
            return Response({"error": "Données incomplètes"}, status=400)

        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            responsable = Responsable.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, Responsable.DoesNotExist):
            return Response({"error": "Lien invalide"}, status=400)

        if not PasswordResetTokenGenerator().check_token(responsable, token):
            return Response({"error": "Token invalide ou expiré"}, status=400)

        responsable.password = make_password(new_password)
        responsable.save()

        return Response({"message": "Mot de passe réinitialisé avec succès"}, status=200)


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.hashers import make_password
from .models import Responsable

class CheckEmailAPIView(APIView):
    def post(self, request):
        email = request.data.get("email")
        try:
            responsable = Responsable.objects.get(Responsable_email=email)
            return Response({"id": responsable.id}, status=200)
        except Responsable.DoesNotExist:
            return Response({"error": "Email introuvable"}, status=404)

class SimplePasswordResetAPIView(APIView):
    def post(self, request):
        responsable_id = request.data.get("id")
        new_password = request.data.get("new_password")

        try:
            responsable = Responsable.objects.get(id=responsable_id)
            responsable.password = make_password(new_password)
            responsable.save()
            return Response({"message": "Mot de passe modifié avec succès"}, status=200)
        except Responsable.DoesNotExist:
            return Response({"error": "Responsable introuvable"}, status=404)
