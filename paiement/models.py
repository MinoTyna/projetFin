from django.db import models
from achats.models import Achat
from django.db.models import Max ,Sum


MOIS_CHOICES = [(i, f"{i} mois") for i in range(1, 6)]

class Paiement(models.Model):
    AchatsID = models.ForeignKey(Achat, on_delete=models.CASCADE, related_name='paiements_details')
    
    Paiement_montant = models.DecimalField(max_digits=10, decimal_places=2)
    
    Paiement_montantchoisi = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        default=None  # Ajouté pour clarté
    )
    
    Paiement_mode = models.CharField(
        max_length=50,
        choices=[
            ('cash', 'Cash'),
            ('carte', 'Carte'),
        ]
    )
    
    Paiement_type = models.CharField(
        max_length=50,
        choices=[
            ('mensuel', 'Mensuel'),
            ('comptant', 'Comptant'),
        ]
    )
    
    Paiement_date = models.DateTimeField(auto_now_add=True)
    
    Paiement_datechoisi = models.DateField(
        null=True,
        blank=True,
        default=None
    )

    def __str__(self):
        return f"Paiement Achat #{self.AchatsID.id} - {self.Paiement_montant} Ar"

    def total_paye(self):
        return self.paiement_set.aggregate(total=Sum('Paiement_montant'))['total'] or 0


class Facture(models.Model):
    numero_facture = models.CharField(max_length=20, unique=True, blank=True)
    paiement = models.OneToOneField(Paiement, on_delete=models.CASCADE, related_name='facture')
    date_creation = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.numero_facture:
            last_num = Facture.objects.aggregate(Max('id'))['id__max'] or 0
            new_num = last_num + 1
            self.numero_facture = f"FACT-{new_num:06d}"
        super().save(*args, **kwargs)

from django.db import models
import random

class PaiementMobile(models.Model):
    numero_client = models.CharField(max_length=20)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    numero_entreprise = models.CharField(
        max_length=20,
        default='0334990938',
        help_text="Numéro mobile de l’entreprise (Airtel Money, Mvola, etc.)"
    )

    mode = models.CharField(
        max_length=50,
        choices=[
            ('airtel', 'Airtel Money'),
            ('mvola', 'MVola'),
            ('orange', 'Orange Money'),
        ],
        default='airtel'
    )

    statut = models.CharField(
        max_length=20,
        choices=[
            ('en_attente', 'En attente'),
            ('reussi', 'Réussi'),
            ('echoue', 'Échoué'),
        ],
        default='en_attente'
    )

    date_paiement = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Paiement {self.montant} Ar par {self.mode} depuis {self.numero_client}"

    # 🔹 Simulation de la vérification du paiement
    def verifier_paiement_mobile(self):
        """Simule une vérification du paiement mobile (succès ou échec)."""
        paiement_valide = random.choice([True, False])

        if paiement_valide:
            self.statut = 'reussi'
            message = f"✅ Paiement confirmé sur {self.numero_entreprise} depuis {self.numero_client}."
        else:
            self.statut = 'echoue'
            message = f"❌ Échec du paiement depuis {self.numero_client}. Veuillez réessayer."

        self.save()
        return message
