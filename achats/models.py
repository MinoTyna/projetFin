from django.db import models
from responsable.models import Responsable
from produit.models import Produit
from client.models import Client
from django.db.models import Max

# Create your models here.
class Achat(models.Model):
    ClientID = models.ForeignKey(Client, on_delete=models.CASCADE)
    ResponsableID = models.ForeignKey(Responsable, on_delete=models.CASCADE)
    ProduitID = models.ForeignKey(Produit, on_delete=models.CASCADE)
    Achat_quantite = models.PositiveIntegerField()
    Achat_montant = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # ✅ à ajouter
    Achat_date = models.DateTimeField(auto_now_add=True)



class Facture(models.Model):
    numero_facture = models.CharField(max_length=20, unique=True, blank=True)
    achat = models.ForeignKey(Achat, on_delete=models.CASCADE, null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)


    def save(self, *args, **kwargs):
        if not self.numero_facture:
            last_facture = Facture.objects.order_by('-id').first()
            last_num = 0
            if last_facture and last_facture.numero_facture:
                # Extraire le nombre dans "FACT-xxxx"
                import re
                match = re.search(r'FACT-(\d+)', last_facture.numero_facture)
                if match:
                    last_num = int(match.group(1))
            new_num = last_num + 1
            self.numero_facture = f"FACT-{new_num:04d}"  # 4 chiffres avec zéro padding
        super().save(*args, **kwargs)

    def __str__(self):
        return self.numero_facture
        
        
        
class Notification(models.Model):
    RECEPTION_CHOICES = [
        ("magasin", "Récupération au magasin"),
        ("livraison", "Livraison à domicile"),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    mode_reception = models.CharField(max_length=20, choices=RECEPTION_CHOICES, default="magasin")
    vue = models.BooleanField(default=False)
    vue_client = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification #{self.id} - {self.client.Client_nom}"


class NotificationProduit(models.Model):
    notification = models.ForeignKey(Notification, related_name="produits", on_delete=models.CASCADE)
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    quantite = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.quantite} x {self.produit.Produit_nom}"
