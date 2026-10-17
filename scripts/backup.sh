#!/bin/bash
# Backs up Postgres, MongoDB and Qdrant into backups/<timestamp>/.
# The data stays in the running containers; the newest 14 backups are kept.
set -euo pipefail
cd "$(dirname "$0")/.."

DEST="backups/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$DEST/qdrant"

echo "Postgres..."
docker exec postgres sh -c 'pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB"' > "$DEST/postgres.dump"

echo "MongoDB..."
docker exec mongodb sh -c 'mongodump --username "$MONGO_INITDB_ROOT_USERNAME" --password "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin --archive --gzip' > "$DEST/mongo.archive.gz"

echo "Qdrant..."
for c in $(curl -sf localhost:6333/collections | python3 -c "import sys,json;print(' '.join(c['name'] for c in json.load(sys.stdin)['result']['collections']))"); do
  snap=$(curl -sf -X POST "localhost:6333/collections/$c/snapshots" | python3 -c "import sys,json;print(json.load(sys.stdin)['result']['name'])")
  curl -sf "localhost:6333/collections/$c/snapshots/$snap" -o "$DEST/qdrant/$c.snapshot"
  curl -sf -X DELETE "localhost:6333/collections/$c/snapshots/$snap" > /dev/null
done

ls -dt backups/*/ | tail -n +15 | xargs -r rm -rf
echo "Backup saved in $DEST"
