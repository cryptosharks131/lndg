#!/usr/bin/env bash

LNDG_SUPERVISOR=${LNDG_SUPERVISOR:-0}

# This init script runs when the image is created, as root
touch /var/log/supervisord.log
chown lndg /var/log/supervisord.log

mkdir -p /lndg/data/
chown -R lndg /lndg

if [ "$LNDG_SUPERVISOR" -eq "1" ]; then
    pip install supervisor
    chgrp lndg /usr/local/etc
    chmod g+rw /usr/local/etc
else
    echo "Supervisor disabled, you need to setup an alternate method to run controller.py"
fi
