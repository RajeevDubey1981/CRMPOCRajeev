#!/bin/bash
# INDcool nightly backup. Runs ON the production server as root (installed at /usr/local/sbin/indcool-backup.sh,
# started by /etc/cron.d/indcool-backup).
#
#  1. creates /var/backups/indcool/daily-<time>: every database dump (indcool, indcool_sales, indcool_marketing,
#     indcool_parts -- each only if present), the uploads folder as files.tar.gz, SHA256SUMS, and a copy of api/.env
#     (the .env stays on the server and is never sent to Drive);
#  2. deletes old app backup folders on the server (older than SERVER_KEEP_DAYS; the newest 3 are always kept);
#  3. uploads the dumps + files archive to Google Drive: <REMOTE>/<time>/ and proves it with `rclone check`;
#  4. only if 3 is verified: deletes every Drive backup set except the newest DRIVE_KEEP_COUNT (default 2; permanent).
#
# Nothing in the databases or the live uploads folder is changed. Exit code is non-zero if anything failed.
# Log: /var/log/indcool-backup.log (written by cron). Needs rclone configured for root (see RCLONE_CONFIG).

set -euo pipefail

REMOTE="${REMOTE:-indcool-gdrive:INDcool Server Backups}"
SERVER_KEEP_DAYS="${SERVER_KEEP_DAYS:-7}"
DRIVE_KEEP_COUNT="${DRIVE_KEEP_COUNT:-2}"
BACKUP_ROOT=/var/backups/indcool
API_DIR=/var/www/indcool/api
DATABASES="indcool indcool_sales indcool_marketing indcool_parts"
export RCLONE_CONFIG="${RCLONE_CONFIG:-/root/.config/rclone/rclone.conf}"

exec 9>/var/lock/indcool-backup.lock
flock -n 9 || { echo "another backup is already running"; exit 1; }

# Failure alert: keep a copy of this run's output and mail it to ALERT_TO if the script ends with an error.
ALERT_TO="${ALERT_TO:-info@indcool.in}"
RUNLOG=$(mktemp /tmp/indcool-backup-run.XXXXXX)
exec > >(tee -a "$RUNLOG") 2>&1
on_exit() {
  code=$?
  if [ "$code" -ne 0 ]; then
    echo "[$(date '+%F %T')] BACKUP FAILED (exit $code)"
    sleep 1
    python3 /usr/local/sbin/indcool-backup-alert.py "$ALERT_TO" "[INDcool] BACKUP FAILED on $(hostname) $(date '+%F %T')" "$RUNLOG" \
      || echo "alert mail could not be sent"
  fi
  rm -f "$RUNLOG"
}
trap on_exit EXIT

STAMP=$(date +%Y%m%d-%H%M%S)
FOLDER="$BACKUP_ROOT/daily-$STAMP"
log() { echo "[$(date '+%F %T')] $*"; }

log "== Backup $STAMP start"
mkdir -p "$FOLDER"; chmod 700 "$FOLDER"

log "1. dumping databases"
for db in $DATABASES; do
  present=$(mysql -N -e "SHOW DATABASES LIKE '$db'")
  if [ "$present" != "$db" ]; then log "   $db: not on this server, skipped"; continue; fi
  mysqldump --single-transaction --routines --triggers --no-tablespaces --default-character-set=utf8mb4 "$db" \
    | gzip > "$FOLDER/db-$db.sql.gz"
  gzip -t "$FOLDER/db-$db.sql.gz"
  log "   ok db-$db.sql.gz $(stat -c %s "$FOLDER/db-$db.sql.gz") bytes"
done

UPLOAD_DIR=$(grep -i '^UPLOAD_DIR=' "$API_DIR/.env" | tail -1 | cut -d= -f2 | tr -d '\r' || true)
case "$UPLOAD_DIR" in /*) ;; *) UPLOAD_DIR=/var/www/indcool/uploads ;; esac
tar -czf "$FOLDER/files.tar.gz" -C "$UPLOAD_DIR" .
gzip -t "$FOLDER/files.tar.gz"
log "   ok files.tar.gz $(stat -c %s "$FOLDER/files.tar.gz") bytes"
( cd "$FOLDER" && sha256sum db-*.sql.gz files.tar.gz > SHA256SUMS && sha256sum -c SHA256SUMS >/dev/null )
cp "$API_DIR/.env" "$FOLDER/api.env"; chmod 600 "$FOLDER/api.env"

log "2. deleting app backups older than $SERVER_KEEP_DAYS days (newest 3 kept)"
cutoff=$(date -d "$SERVER_KEEP_DAYS days ago" +%s)
find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d \( -name 'predeploy-*' -o -name 'daily-*' \) -printf '%T@ %f\n' \
  | sort -rn | tail -n +4 | while read -r t name; do
    if [ "${t%.*}" -lt "$cutoff" ]; then rm -rf "${BACKUP_ROOT:?}/$name"; log "   deleted $name"; fi
  done

log "3. uploading to $REMOTE/$STAMP"
rclone copy "$FOLDER" "$REMOTE/$STAMP" --exclude api.env --checksum 2>&1 | grep -v NOTICE || true
if ! rclone check "$FOLDER" "$REMOTE/$STAMP" --exclude api.env 2>&1 | grep -q ' 0 differences found'; then
  log "   FAILED: Drive copy does not match. Old Drive backups were NOT deleted."
  exit 1
fi
log "   Drive check passed"

log "4. deleting old Drive backups (keeping the newest $DRIVE_KEEP_COUNT)"
rclone lsf --dirs-only "$REMOTE" | tr -d '/' | grep -E '^[0-9]{8}-[0-9]{6}$' | sort -r | tail -n +"$((DRIVE_KEEP_COUNT + 1))" | while read -r name; do
  rclone purge "$REMOTE/$name" --drive-use-trash=false 2>&1 | grep -v NOTICE || true
  log "   deleted Drive set $name"
done

log "== Backup $STAMP finished: all steps ok"
