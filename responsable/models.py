# from django.db import models
# class Responsable(models.Model):
#     ROLE_CHOICES = [
#         ('admin', 'Admin'),
#         ('vendeur', 'Vendeur'),
#     ]
#     clerk_id = models.CharField(max_length=100, unique=True, null=True, blank=True)  # ID Clerk unique
#     Responsable_email = models.EmailField(unique=True)  # Ajoute unique pour éviter les doublons
#     Responsable_nom = models.CharField(max_length=100, null=True, blank=True, default=None)
#     Responsable_prenom = models.CharField(max_length=100, null=True, blank=True, default=None)
#     Responsable_adresse = models.TextField(null=True, blank=True, default=None)
#     Responsable_telephone = models.CharField(max_length=20, null=True, blank=True, default=None)
#     Responsable_role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='vendeur')
#     Responsable_photo = models.ImageField(upload_to='responsables/photos/', blank=True, null=True)
#     date_creation = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.prenom or ''} {self.nom or ''} - {self.role}"

from django.db import models

class Responsable(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('vendeur', 'Vendeur'),
    ]
    Responsable_email = models.EmailField(unique=True)
    Responsable_nom = models.CharField(max_length=100, null=True, blank=True, default=None)
    Responsable_prenom = models.CharField(max_length=100, null=True, blank=True, default=None)
    Responsable_adresse = models.TextField(null=True, blank=True, default=None)
    Responsable_telephone = models.CharField(max_length=20, null=True, blank=True, default=None)
    Responsable_role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='vendeur')
    Responsable_photo = models.ImageField(upload_to='responsables/photos/', blank=True, null=True)

    # 🔒 Champ mot de passe sécurisé
    password = models.CharField(max_length=128, null=True, blank=True)

    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.Responsable_prenom or ''} {self.Responsable_nom or ''} - {self.Responsable_role}"
