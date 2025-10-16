# --- Étape 1 : Image de base ---
FROM python:3.13-slim

# --- Étape 2 : Variables d'environnement ---
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# --- Étape 3 : Copie du code ---
WORKDIR /app
COPY . /app

# --- Étape 4 : Installation des dépendances Python ---
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# --- Étape 5 : Commande de démarrage ---
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
