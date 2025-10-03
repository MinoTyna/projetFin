from django.urls import path
from .views import EnregistrerAchatAPIView, ListAchatAPIView, AchatDeleteAPIView,AchatListAPIView,FactureAllView,TotalAchatsParResponsableAPIView,ProduitSortieTotalAPIView,ProduitPlusVenduAPIView,FactureDates,PaiementListView,ProduitsParResponsableAPIView,StatistiquesResponsableAPIView,ClientsFidelesAPIView,ProduitSortieTotalAPI,StatistiquesResponsableAPI,UpdateAchatsAPIView,ValiderCommande,NotificationList,AccepterNotification,NotificationAccepteesParClient,MarkNotificationReadClient,NotificationDetailById

urlpatterns = [
    path('post', EnregistrerAchatAPIView.as_view(), name='enregistrer-achats'),
    path('get/<int:client_id>', ListAchatAPIView.as_view(), name='liste-achats'),
    path('get', AchatListAPIView.as_view(), name='liste-achats'),
    path('statique', StatistiquesResponsableAPIView.as_view(), name='liste-achats'),
    path('global', StatistiquesResponsableAPI.as_view(), name='liste-achats'),
    path('client', ClientsFidelesAPIView.as_view(), name='liste-achats'),
    path('sortie', ProduitSortieTotalAPIView.as_view(), name='sortie-achats'),
    path('sorti', ProduitSortieTotalAPI.as_view(), name='sortie-achats'),
    path('produit/vendu', ProduitPlusVenduAPIView.as_view(), name='vendu-achats'),

    path('total/<int:responsable_id>', TotalAchatsParResponsableAPIView.as_view(), name='facture-achats'),
    path('facture', FactureAllView.as_view(), name='facture'),
    path('paiement', PaiementListView.as_view(), name='paiement'),
    path('factures/<int:client_id>/', FactureDates.as_view(), name='facture'),
    path('delete/<int:achat_id>', AchatDeleteAPIView.as_view(), name='liste-achats'),
    path("update/<int:client_id>/", UpdateAchatsAPIView.as_view(), name="update-achats"),
    path('commande/', ValiderCommande.as_view(), name='valider-commande'),
    path('notifications/', NotificationList.as_view(), name='notifications-list'),
    path('notifications/<int:pk>/accepter/', AccepterNotification.as_view(), name='accepter-notification'),
    path('notifications/<int:client_id>/acceptes/', NotificationAccepteesParClient.as_view(), name='notifications_acceptees_par_client'),
    path('notifications/<int:notification_id>/mark-read/', MarkNotificationReadClient.as_view()),
    path( 'notifications/<int:notif_id>/',
        NotificationDetailById.as_view(),
        name='notification-detail'),






]
