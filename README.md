# lndg
Lite GUI web interface to analyze lnd data and manage your node with automation.

## Setup
1. Running `bitcoind`
2. Running `lnd`
3. Clone respository `git clone https://github.com/cryptosharks131/lndg.git`
4. Change directory into the repo `cd lndg`
5. Setup a python virtual environment `virtualenv .venv`
6. Install required dependencies `.venv/bin/pip install -r requirements.txt`
7. Initialize a settings.py file for your django site `.venv/bin/python initialize.py`
8. Make migrations and migrate all database objects `.venv/bin/python manage.py makemigrations gui && .venv/bin/python manage.py migrate`
9. Run the server via chosen webserver or via python development server `.venv/bin/python manage.py runserver`

## Backend Data Refreshes
The file `jobs.py` inside lndg/gui/ serves to update the backend database with the most up to date information.  This reduces the amount of calls made when a user refreshes the front end and enables the rest api usage to fetch data from your lnd node.

You will need to setup a systemd/crontab (linux) or task scheduler (windows) to run this file at your specified refresh interval.  A refresh of 15-60 seconds is advisable for the best experience and may depend on how quickly your machine is capable of handling the file execution. This can be ran manually with: `.venv/bin/python gui/jobs.py`

## Automated Rebalancing
The file `rebalancer.py` inside lndg/gui/ serves to rebalance any channels that meet the specifications set on your lndg dashboard.  Default values are set upon the first run of the rebalancer file.  You can review this file to find the default values.

You will need to setup a systemd/crontab (linux) or task scheduler (windows) to run this file at your specified refresh interval.  A refresh of 15-60 seconds is advisable for the best experience and may depend on how quickly your machine is capable of handling the file execution. This can be ran manually with: `.venv/bin/python gui/rebalancer.py`

## API Backend
The following data can be accessed at the /api endpoint: `payments`, `invoices`, `forwards`, `channels`, and `rebalancer`

## Preview Screens
### Main Dashboard
![image](https://user-images.githubusercontent.com/38626122/132701345-7129e4e5-09b8-483e-96eb-bf003171ed3f.png)
![image](https://user-images.githubusercontent.com/38626122/132701473-33611c23-cb91-4496-a9ee-c276f1b35f34.png)
![image](https://user-images.githubusercontent.com/38626122/132701498-5cefa10f-00b3-45e3-9a38-e6512d47b750.png)
![image](https://user-images.githubusercontent.com/38626122/132701518-41e585ae-bac3-413b-a6a2-c202e20fd7f9.png)
![image](https://user-images.githubusercontent.com/38626122/132701532-a129f74f-ee6e-4f03-89c8-e82eef775ab1.png)

### Peers, Balances and Routes All Open In Separate Screens
![image](https://user-images.githubusercontent.com/38626122/132701553-bbab3f27-ac72-4de6-9591-506c6740579b.png)
![image](https://user-images.githubusercontent.com/38626122/132861336-3cb02cad-2b09-4548-8186-a93b2482c40d.png)

### Browsable API at `/api` (json format available with url appended with `?format=json`)
![image](https://user-images.githubusercontent.com/38626122/134045960-13019cd9-715d-43aa-873d-414626369373.png)

### New! View Keysend Messages (you can only receive these if you have `accept-keysend=true` in lnd.conf)
![image](https://user-images.githubusercontent.com/38626122/134045287-086d56e3-5959-4f5f-a06e-cb6d2ac4957c.png)
