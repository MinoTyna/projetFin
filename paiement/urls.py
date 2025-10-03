# from django.urls import path
# from .views import PaiementCreateView, PaiementListView, VerifierPaiementListView, PaiementDeleteAPIView, ListeResteAPayerParClient,ListePayerParClient,PaiementUpdateView,SmsVerifierByClientView,PaiementView,RepaiementCreateView

# urlpatterns = [
#     path('post', PaiementCreateView.as_view(), name='enregistrer-paiement'),
#     path('repaiement', RepaiementCreateView.as_view(), name='enregistrer-paiement'),
#     path('get', PaiementListView.as_view(), name='liste-paiement'),
#     path('verifier/', VerifierPaiementListView.as_view(),name='verification'),
#     path('sms/<int:client_id>', SmsVerifierByClientView.as_view(),name='sms'),
#     path('facture', PaiementView.as_view(),name='facture'),
#     path('delete/<int:paiement_id>', PaiementDeleteAPIView.as_view(), name='delete-paiement'),
#     path('update/<int:pk>', PaiementUpdateView.as_view(), name='update-paiement'),
#     path('get/client', ListeResteAPayerParClient.as_view(), name='delete-paiement'),
#     path('get/<int:client_id>', ListePayerParClient.as_view(), name='delete-paiement'),

# ]
from django.urls import path
from .views import PaiementCreateView, PaiementListView, VerifierPaiementListView, PaiementDeleteAPIView, ListeResteAPayerParClient,ListePayerParClients,ListePayerParClient,PaiementUpdateView,SmsVerifierByClientView,RepaiementCreateView,PaiementView,ChiffreAffairesAPIView

urlpatterns = [
    path('post', PaiementCreateView.as_view(), name='enregistrer-paiement'),
    path('repaiement', RepaiementCreateView.as_view(), name='enregistrer-paiement'),
    path('get', PaiementListView.as_view(), name='liste-paiement'),
    path('affaire', ChiffreAffairesAPIView.as_view(), name='liste-paiement'),
    path('facture', PaiementView.as_view(),name='facture'),
    path('verifier/', VerifierPaiementListView.as_view(),name='verification'),
    path('sms/<int:client_id>', SmsVerifierByClientView.as_view(),name='sms'),
    path('delete/<int:paiement_id>', PaiementDeleteAPIView.as_view(), name='delete-paiement'),
    path('update/<int:pk>', PaiementUpdateView.as_view(), name='update-paiement'),
    path('get/client', ListeResteAPayerParClient.as_view(), name='delete-paiement'),
    path('get/<int:client_id>/<str:date_achat>', ListePayerParClients.as_view(), name='delete-paiement'),
    path('get/<int:client_id>', ListePayerParClient.as_view(), name='liste-payer-client'),


]