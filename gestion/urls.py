from django.urls import path
from .views import GestionCreateView, GestionListView,GestiontDeleteAPIView

urlpatterns = [
    path('post', GestionCreateView.as_view(), name='inserer-produit'),
    path('get', GestionListView.as_view(), name='liste-insertions'),
    path('delete/<int:insertion_id>', GestiontDeleteAPIView.as_view(), name='deleteliste-insertions'),
]
