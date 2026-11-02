#!/bin/bash
# Daily backup of the mirrored indcool database on Server B (the replica/standby).
# Each day's backup is a separate file -- never overwritten -- kept for KEEP_DAYS, then auto-deleted.
# Installed as a root cron job (see scripts/_install_daily_backup.py).

set -euo pipefail

KEEP_DAYS=30
BACKUP_DIR=/var/backups/indcool-replica
STAMP=$(date +%Y-%m-%d)
OUT="$BACKUP_DIR/backup-$STAMP.sql.gz"

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

mysqldump --defaults-extra-file=/root/.my.cnf --single-transaction --routines --triggers indcool | gzip > "$OUT"
gzip -t "$OUT"
chmod 600 "$OUT"

# Delete backups older than KEEP_DAYS (each day's file is independent -- today's run never touches yesterday's file)
find "$BACKUP_DIR" -name 'backup-*.sql.gz' -mtime "+$KEEP_DAYS" -delete

echo "Backup complete: $OUT ($(stat -c %s "$OUT") bytes)"
