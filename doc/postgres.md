# LNDg Postgres Setup

- **You will need to fill in the proper password below in the paths marked `<psql_password>`.**

## Postgres Installation
Install postgres  
`sudo apt install postgresql`

Switch to postgres user and open the client  
`sudo su - postgres`  
`psql`

Create the LNDg Database - Be sure to replace the password with your own  
`create user lndg;create database lndg LOCALE 'en_US.UTF-8';alter role lndg with password '<psql_password>';grant all privileges on database lndg to lndg;alter database lndg owner to lndg;`

Exit the postgres client and user  
`\q`  
`exit`

## Setting up LNDg with postgres
Enter the LNDg installation folder  
`cd lndg`

Upgrade setuptools and get required packages  
`.venv/bin/pip install --upgrade setuptools`  
`sudo apt install gcc python3-dev libpq-dev`

Build psycopg2 for postgres connection  
`.venv/bin/pip install psycopg2`

Update the  `DATABASES` section of `lndg/lndg/settings.py`, be sure to replace the password  
```
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'lndg',
        'USER': 'lndg',
        'PASSWORD': '<psql_password>',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```
Initialize the postgres database  
`.venv/bin/python manage.py migrate`

## OPTIONAL: Migrating An Existing Database
Stop the LNDg services controller and web service  
`sudo systemctl stop lndg-controller.service`  
`sudo systemctl stop uwsgi.service`

Dump current data to json format  
`.venv/bin/python manage.py dumpdata gui.channels gui.peers gui.rebalancer gui.localsettings gui.autopilot gui.autofees gui.failedhtlcs gui.avoidnodes gui.peerevents > dump.json`

Import the dump  
`.venv/bin/python manage.py loaddata dump.json`

## Finishing Setup
Recreate a login user - any username and password may be used  
`.venv/bin/python manage.py createsuperuser`

Restart the LNDg controller and web service  
`sudo systemctl restart lndg-controller.service`  
`sudo systemctl restart uwsgi.service`