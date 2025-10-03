from django.db import models

from responsable.models import Responsable
from produit.models import Produit

class Gestion(models.Model):
    ResponsableID = models.ForeignKey(Responsable, on_delete=models.CASCADE)
    ProduitID = models.ForeignKey(Produit, on_delete=models.CASCADE)
    Gestion_date = models.DateTimeField(auto_now_add=True)
    Gestion_quantite = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.utilisateur.nom} a inséré {self.quantite} de {self.produit.nom}"
