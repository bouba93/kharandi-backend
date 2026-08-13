#!/bin/bash
# scripts/setup_dev.sh — Installation et configuration de l'environnement de développement
set -e

echo "🚀 Configuration de Kharandi Backend..."

# 1. Créer et activer un virtualenv
python3 -m venv venv
source venv/bin/activate

# 2. Installer les dépendances
pip install --upgrade pip
pip install -r requirements.txt

# 3. Copier le fichier .env
if [ ! -f .env ]; then
  cp .env.example .env
  echo "📋 Fichier .env créé depuis .env.example"
  echo "⚠️  Veuillez compléter les variables dans .env avant de continuer."
fi

# 4. Appliquer les migrations + créer la table de cache
echo "📦 Application des migrations..."
python manage.py migrate
echo "🗄  Création de la table de cache Django..."
python manage.py createcachetable

# 5. Créer les données initiales
echo "🌱 Création des données initiales..."
python manage.py seed_data

# 6. Activer les tâches planifiées (cron système)
echo "⏰ Activation des tâches CRON..."
python manage.py crontab add
python manage.py crontab show

# 7. Créer un superutilisateur admin
echo ""
echo "👤 Création du superutilisateur admin Django..."
python manage.py createsuperuser

echo ""
echo "✅ Configuration terminée !"
echo ""
echo "Démarrez le serveur :  python manage.py runserver"
echo "Voir les crons actifs : python manage.py crontab show"
echo "Documentation API :    http://localhost:8000/api/docs/"
