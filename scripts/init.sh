#!/usr/bin/env bash

# This init script runs when the container start, as rootless

LNDG_SUPERVISOR=${LNDG_SUPERVISOR:-0}
LNDG_NETWORK=${LNDG_NETWORK:-mainnet}
LNDG_SERVER=${LNDG_SERVER:-localhost:10009}

echo "Initializing lndg for $LNDG_NETWORK network running on docker"

if [ "$LNDG_SUPERVISOR" -eq "1" ]; then
    echo "Initializing with supervisor running as lndg user"
    python initialize.py \
        -net $LNDG_NETWORK \
        -rpc $LNDG_SERVER \
        --docker \
        --supervisord \
        --sduser lndg
else
    echo "Initializing without supervisor"
    python initialize.py \
        -net $LNDG_NETWORK \
        -rpc $LNDG_SERVER \
        --docker
fi
