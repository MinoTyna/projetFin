"""
Django settings for monbackend project.
"""

import os
from pathlib import Path
import dj_database_url
import cloudinary
import cloudinary.uploader
import cloudinary.api
from dotenv import load_dotenv

load_dotenv()

# --- BASE ---
BASE_DIR = Path(__file__).resolve().parent.parent

# --- SÉCURITÉ ---
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-gybr)@9q7a&l&k$d6%xtwu51v3m5q%95hja(#%v2yno^t2d5=a"
)
DEBUG = os.getenv("DEBUG", "False") == "True"

ALLOWED_HOSTS = [
    "api.auf-sarlu.mg",
    "app.auf-sarlu.mg",
    "venteproduit.auf-sarlu.mg",
    "lu.auf-sarlu.mg",
    "vente.auf-sarlu.mg",
    "myapp.auf-sarlu.mg",
    "myvente.auf-sarlu.mg",
    "localhost",
    "127.0.0.1",
    "projetfin.onrender.com"
]

# --- APPLICATIONS ---
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "cloudinary",
    "cloudinary_storage",
    # apps locales
    "responsable",
    "client",
    "produit",
    "gestion",
    "paiement",
    "achats",
]

# --- MIDDLEWARE ---
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# --- CORS ---
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "https://venteproduit.auf-sarlu.mg",
    "https://vente.auf-sarlu.mg",
    "https://myvente.auf-sarlu.mg",
    "https://myapp.auf-sarlu.mg",
    "http://localhost:3000",
]

# --- DATABASE ---
DATABASES = {
    "default": dj_database_url.parse(
        os.getenv(
            "DATABASE_URL",
            "postgresql://postgre:5kr7i1RC8OFbbsX3fzqptTAE3gP91USM@dpg-d3o83ud6ubrc73a85cj0-a.oregon-postgres.render.com/aufsarl"
        ),
        conn_max_age=600,
        ssl_require=True,
    )
}

# --- REST FRAMEWORK ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
}

# --- MOTS DE PASSE ---
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- INTERNATIONALISATION ---
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# --- EMAIL ---
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "tinyroane@gmail.com"
EMAIL_HOST_PASSWORD = "vtpu jouc llfs nhau"
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# --- FICHIERS STATIQUES ET MÉDIAS ---
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Cloudinary configuration
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", "dywaprcfa"),
    api_key=os.getenv("CLOUDINARY_API_KEY", "342866519857239"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET", "wC3unuMlOKDvDkq3JZLDooMW8GE"),
    secure=True,
)

# Tous les fichiers uploadés iront dans Cloudinary
DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"

# Si tu veux garder un MEDIA_ROOT local pour développement
if DEBUG:
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"

# --- AUTRES ---
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
WSGI_APPLICATION = "monbackend.wsgi.application"
ROOT_URLCONF = "monbackend.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]