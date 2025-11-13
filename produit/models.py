from django.db import models
from django.core.validators import MinValueValidator

class Produit(models.Model):
    CATEGORIES = [
        ("Electromenager", "Électroménager"),
        ("MaisonCuisine", "Maison & Cuisine"),
        ("MobilierLiterie", "Mobilier & Literie"),
        ("Electronique", "Électronique & Multimédia"),
        ("Mode", "Mode & Accessoires"),
        ("Transport", "Véhicules & Transport"),
        ("Energie", "Énergie & Solaire"),
    ]

    Produit_nom = models.CharField(max_length=40)
    Produit_description = models.TextField(blank=True, null=True)
    Produit_reference = models.TextField(blank=True, null=True)
    Produit_prix = models.IntegerField()
    
    # ⚡ Supabase Storage → stocker le nom du fichier
    Produit_photo = models.ImageField(upload_to='', blank=True, null=True)


    
    date = models.DateTimeField(auto_now_add=True)

    Produit_quantite = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )

    Produit_categorie = models.CharField(
        max_length=30,
        choices=CATEGORIES,
        default="MaisonCuisine"
    )

    def __str__(self):
        return f"{self.Produit_nom} ({self.Produit_categorie})"

    # ⚡ Générer l'URL publique de Supabase
    def get_photo_url(self):
        if self.Produit_photo:
            return f"https://rcbhcqyypiaatvcyolnw.supabase.co/storage/v1/object/public/media/{self.Produit_photo}"
        return None
