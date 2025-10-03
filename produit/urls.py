from django.urls import path
from .views import ProduitCreateAPIView, ProduitListAPIView,ProduitDeleteAPIView,ProduitUpdateAPIView,ProduitTotalAPIView

urlpatterns = [
    path('post', ProduitCreateAPIView.as_view(), name='enregistrer-produit'),
    path('get', ProduitListAPIView.as_view(), name='liste-produit'),
    path('total', ProduitTotalAPIView.as_view(), name='total-produit'),
    path('delete/<int:produit_id>', ProduitDeleteAPIView.as_view(), name='delete-produit'),
    path('update/<int:produit_id>', ProduitUpdateAPIView.as_view(), name='update-produit'),
]
