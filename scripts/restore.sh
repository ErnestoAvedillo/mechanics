#!/bin/bash
# Restores a backup made by scripts/backup.sh. Usage: scripts/restore.sh backups/<timestamp>
# REPLACES the current Postgres, MongoDB and Qdrant data with the backup contents.
set -euo pipefail
cd "$(dirname "$0")/.."

DIR="${1:-}"
if [ -z "$DIR" ] || [ ! -d "$DIR" ]; then
  echo "Usage: $0 backups/<timestamp>"
  exit 1
fi

echo "This REPLACES the current data (Postgres, MongoDB, Qdrant) with the contents of $DIR."
printf "Type 'restore' to continue: "
read -r ans
[ "$ans" = "restore" ] || { echo "Cancelled"; exit 1; }

echo "Postgres..."
docker exec -i postgres sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists' < "$DIR/postgres.dump"

echo "MongoDB..."
docker exec -i mongodb sh -c 'mongorestore --username "$MONGO_INITDB_ROOT_USERNAME" --password "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin --archive --gzip --drop' < "$DIR/mongo.archive.gz"

echo "Qdrant..."
for f in "$DIR"/qdrant/*.snapshot; do
  [ -e "$f" ] || continue
  c="$(basename "$f" .snapshot)"
  curl -sf -X POST "localhost:6333/collections/$c/snapshots/upload?priority=snapshot" -F "snapshot=@$f" > /dev/null
  echo "  restored collection $c"
done

echo "Restore finished from $DIR"
