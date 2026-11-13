#!/usr/bin/env bash
# Usage: scripts/restore.sh path/to/db-YYYYMMDD-HHMMSS.sqlite3
set -euo pipefail

if [[ $# -ne 1 || ! -f "$1" ]]; then
    echo "Uso: scripts/restore.sh <arquivo.sqlite3>" >&2
    exit 1
fi

cd "$(dirname "$0")/.."
backup_file="$1"
read -r -a compose_cmd <<< "${COMPOSE:-docker compose}"

result="$(python3 -c 'import pathlib, sqlite3, sys
try:
    con = sqlite3.connect(pathlib.Path(sys.argv[1]).resolve().as_uri() + "?mode=ro", uri=True)
    print(con.execute("PRAGMA integrity_check").fetchone()[0])
except sqlite3.DatabaseError as erro:
    print(erro)' "$backup_file")"
if [[ "$result" != "ok" ]]; then
    echo "Arquivo de backup inválido: $result" >&2
    exit 1
fi

echo "Isto substitui o banco atual pelo backup $backup_file."
if ! read -r -p "Digite SIM para continuar: " answer </dev/tty || [[ "$answer" != "SIM" ]]; then
    echo "Restauração cancelada." >&2
    exit 1
fi

"$(dirname "$0")/backup.sh"

"${compose_cmd[@]}" stop app
container="$("${compose_cmd[@]}" ps -a -q app)"
docker cp "$backup_file" "$container:/data/restore-tmp.sqlite3"
"${compose_cmd[@]}" run --rm -T --no-deps --user root --entrypoint sh app -c \
    'rm -f /data/db.sqlite3-wal /data/db.sqlite3-shm && mv /data/restore-tmp.sqlite3 /data/db.sqlite3 && chown app:app /data/db.sqlite3'
"${compose_cmd[@]}" start app
echo "Banco restaurado a partir de $backup_file."
