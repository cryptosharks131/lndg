#!/bin/bash
set -eo pipefail

python initialize.py -net 'signet' -server 'playground-lnd:10009'
python manage.py migrate
python manage.py runserver 0.0.0.0:8000