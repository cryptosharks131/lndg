#!/usr/bin/env bash
set -e

LNDG_SUPERVISOR=${LNDG_SUPERVISOR:-0}
LNDG_LISTEN=${LNDG_LISTEN:-0.0.0.0}
LNDG_PORT=${LNDG_PORT:-8000}

scripts/init.sh

if [ "$LNDG_SUPERVISOR" -eq "1" ]; then
    echo "Starting supervisor"
    supervisord
else
    echo "Supervisor disabled, you need to setup an alternate method to run controller.py"
fi

echo "Starting lndg server"
python manage.py runserver $LNDG_LISTEN:$LNDG_PORT
