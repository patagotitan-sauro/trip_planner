#!/usr/bin/env bash
# Cron example: 0 3 * * * COMPOSE="docker compose -f compose.yaml" /path/to/trip_planner/scripts/backup.sh
set -euo pipefail

cd "$(dirname "$0")/.."
read -r -a compose_cmd <<< "${COMPOSE:-docker compose}"
destination="${BACKUP_DIR:-$HOME/backups/trip-planner}"
keep="${BACKUP_KEEP:-14}"
stamp="$(date +%Y%m%d-%H%M%S)"
temp="/tmp/backup-$stamp.sqlite3"
file="$destination/db-$stamp.sqlite3"

# SQLite backup API: consistent while the app runs (AGENTS.md section 12).
copy_py='import sqlite3, sys
source = sqlite3.connect("/data/db.sqlite3")
target = sqlite3.connect(sys.argv[1])
source.backup(target)
print(target.execute("PRAGMA integrity_check").fetchone()[0])
target.close()
source.close()'

trap '"${compose_cmd[@]}" exec -T app rm -f "$temp" || true' EXIT

mkdir -p "$destination"
result="$("${compose_cmd[@]}" exec -T app python -c "$copy_py" "$temp")"
if [[ "$result" != "ok" ]]; then
    echo "Backup falhou na verificação de integridade: $result" >&2
    exit 1
fi

container="$("${compose_cmd[@]}" ps -q app)"
docker cp "$container:$temp" "$file"

ls -1t "$destination"/db-*.sqlite3 | tail -n +"$((keep + 1))" | xargs -r rm --
echo "Backup salvo em $file (mantidas as $keep cópias mais recentes)."
