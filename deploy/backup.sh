#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# backup.sh — Sauvegarde PostgreSQL + médias du VPS YIGUI
#
# Sur le serveur :  bash /opt/kharandi/deploy/backup.sh
# Automatiser (cron root, 3 h du matin) :
#   0 3 * * * bash /opt/kharandi/deploy/backup.sh >> /var/log/kharandi-backup.log 2>&1
# ══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/kharandi}"
BACKUP_DIR="${BACKUP_DIR:-/opt/kharandi-backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
STAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p "$BACKUP_DIR"
cd "$APP_DIR"

DB_USER="$(grep -E '^POSTGRES_USER=' .env | cut -d= -f2- || echo kharandi_user)"
DB_NAME="$(grep -E '^POSTGRES_DB=' .env   | cut -d= -f2- || echo kharandi_db)"

echo "==> Sauvegarde base de données ($DB_NAME)"
docker compose exec -T db pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "${BACKUP_DIR}/db_${STAMP}.sql.gz"

echo "==> Sauvegarde des médias"
docker run --rm \
    -v kharandi_media_data:/data:ro \
    -v "${BACKUP_DIR}":/backup \
    alpine tar czf "/backup/media_${STAMP}.tar.gz" -C /data . 2>/dev/null \
    || echo "    (volume médias introuvable — ignoré)"

echo "==> Purge des sauvegardes de plus de ${RETENTION_DAYS} jours"
find "$BACKUP_DIR" -name '*.gz' -mtime "+${RETENTION_DAYS}" -delete

echo "==> Terminé :"
ls -lh "$BACKUP_DIR" | tail -5
