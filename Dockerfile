# --- Étape 1 : Image de base ---
FROM python:3.13-slim

# --- Étape 2 : Variables d'environnement pour pip ---
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# --- Étape 3 : Installer les dépendances système ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmariadb-dev \
    libmariadb-dev-compat \
    && rm -rf /var/lib/apt/lists/*

# --- Étape 4 : Définir le répertoire de travail ---
WORKDIR /app

# --- Étape 5 : Copier requirements ---
COPY requirements.txt .

# --- Étape 6 : Installer les dépendances Python ---
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# --- Étape 7 : Copier le code de l'application ---
COPY . .

# --- Étape 8 : Commande par défaut (Django avec hot-reload) ---
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
