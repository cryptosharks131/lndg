# lndg
Lite GUI web interface to analyze lnd data and manage your node with automation.

## Setup
1. Clone respository `git clone https://github.com/cryptosharks131/lndg.git`
2. Change directory into the repo `cd lndg`
3. Make sure you have python virtualenv installed `apt install virtualenv`
4. Setup a python3 virtual environment `virtualenv -p python3 .venv`
5. Install required dependencies `.venv/bin/pip install -r requirements.txt`
6. Initialize a settings.py file for your django site `.venv/bin/python initialize.py`
7. Migrate all database objects `.venv/bin/python manage.py migrate`
8. Run the server via chosen webserver or via python development server `.venv/bin/python manage.py runserver <your_node_ip>:80`
9. Generate some initial data for your web GUI `.venv/bin/python jobs.py`

Note: If you are not using the default path for LND `~/.lnd` you can add a custom path in the django settings file `lndg/settings.py`

## Updating
1. Make sure you are in the lndg folder `cd lndg`
2. Pull the new files `git pull`
3. Migrate any database changes `.venv/bin/python manage.py migrate`

## Backend Data Refreshes and Automated Rebalancing
The files `jobs.py` and `rebalancer.py` inside lndg/gui/ serve to update the backend database with the most up to date information and rebalance any channels based on your lndg dashboard settings and requests. A refresh interval of at least 15-30 seconds is recommended for the best user experience.  

You can find instructions on settings these files up to run in the background via systemd [here](https://github.com/cryptosharks131/lndg/blob/master/systemd.md).  
If you are familiar with crontab, this is also an option for setting up these files to run on a frequent basis, however it only has a resolution of 1 minute.  
A bash script has also been included to install the systemd setup. `sudo bash systemd.sh`

## Nginx Webserver
If you would like to serve the dashboard at all times, it is recommended to setup a proper production webserver to host the site.  
A bash script has been included to help aide in the setup of a nginx webserver. `sudo bash nginx.sh`

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
