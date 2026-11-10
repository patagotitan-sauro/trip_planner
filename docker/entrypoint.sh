#!/bin/sh
# Runs before the main command. Safe to run before the Django project exists
# (see `make bootstrap`): the steps are skipped when manage.py is missing.
set -eu

if [ -f manage.py ] && [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    python manage.py migrate --noinput
fi

if [ -f manage.py ] && [ "${RUN_COLLECTSTATIC:-0}" = "1" ]; then
    python manage.py collectstatic --noinput
fi

exec "$@"
