#!/bin/bash
set -e

echo "⏳ Kharandi Backend — démarrage..."

# Appliquer les migrations
echo "📦 Application des migrations..."
python manage.py migrate --noinput

# Créer la table de cache (DatabaseCache)
echo "🗄  Initialisation de la table de cache..."
python manage.py createcachetable

# Collecter les fichiers statiques
echo "🗂  Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

# Activer les tâches CRON
echo "⏰ Activation des tâches CRON..."
python manage.py crontab add

echo "✅ Prêt — lancement du serveur."
exec "$@"
