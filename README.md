# lndg
Lite GUI web interface to analyze lnd data and manage your node with automation.

## Setup
1. Run bitcoind
2. Run lnd
3. Build required py file for your system to interact with lnd grpc: https://github.com/lightningnetwork/lnd/blob/master/docs/grpc/python.md#setup-and-installation
4. Clone respository
5. Place the 2 ouput files from step 3 inside the repository at: lndg/gui/
6. A settings file is required at lndg/settings.py (default django setting file + 'gui' + 'rest_framework' + 'qr_code' added to your installed apps inside the file)
7. Make migrations and migrate all database objects (python manage.py makemigrations && python manage.py migrate)
8. Run the server via chosen webserver or via python development server (python manage.py runserver IP:PORT)

## Backend Data Refreshes
The file `jobs.py` inside lndg/gui/ serves to update the backend database with the most up to date information.  This reduces the amount of calls made when a user refreshes the front end and enables the rest api usage to fetch data from your lnd node.

You will need to setup a crontab (linux) or task scheduler (windows) to run this file at your specified refresh interval.  A refresh of 15-60 seconds is advisable for the best experience and may depend on how quickly your machine is capable of handling the file execution.

## Automated Rebalancing
The file `rebalancer.py` inside lndg/gui/ serves to rebalance any channels that meet the specifications set on your lndg dashboard.  Default values are set upon the first run of the rebalancer file.  You can review this file to find the default values.

You will need to setup a crontab (linux) or task scheduler (windows) to run this file at your specified refresh interval.  A refresh of 15-60 seconds is advisable for the best experience and may depend on how quickly your machine is capable of handling the file execution.
