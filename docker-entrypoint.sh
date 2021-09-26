#!/bin/bash
set -eo pipefail

python initialize.py -net 'mainnet' -server 'localhost:10009'
python manage.py migrate
sleep 30
python manage.py runserver 0.0.0.0:8000