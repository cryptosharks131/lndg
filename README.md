# lndg
Lite GUI web interface to analyze lnd data and manage your node with automation.

## Docker Installation (requires docker and docker-compose be installed)
### Build the image
1. Clone respository `git clone https://github.com/cryptosharks131/lndg.git`
2. Change directory into the repo `cd lndg`
3. Customize `docker-compose.yaml` if you like and then build/deploy your docker image: `docker-compose up -d`
4. LNDg should now be available on port `8889`

### Notes
1. Unless you save your `db.sqlite3` file before destroying your container, this data will be lost and rebuilt when making a new container. However, some data such as rebalances from previous containers cannot be rebuilt.
2. You can make this file persist by initializing it first locally `touch /root/lndg/db.sqlite3` and then mapping it locally in your docker-compose file under the volumes. `/root/lndg/db.sqlite3:/lndg/db.sqlite3:rw`

## Manual Installation
### Step 1 - Install lndg
1. Clone respository `git clone https://github.com/cryptosharks131/lndg.git`
2. Change directory into the repo `cd lndg`
3. Make sure you have python virtualenv installed `apt install virtualenv`
4. Setup a python3 virtual environment `virtualenv -p python3 .venv`
5. Install required dependencies `.venv/bin/pip install -r requirements.txt`
6. Initialize some settings for your django site (see notes below) `.venv/bin/python initialize.py`
7. Migrate all database objects `.venv/bin/python manage.py migrate`
8. Generate some initial data for your dashboard `.venv/bin/python jobs.py`
9. Run the server via a python development server `.venv/bin/python manage.py runserver 0.0.0.0:8889`

### Step 2 - Setup Backend Data and Automated Rebalancing
The files `jobs.py` and `rebalancer.py` inside lndg/gui/ serve to update the backend database with the most up to date information and rebalance any channels based on your lndg dashboard settings and requests. A refresh interval of at least 15-30 seconds is recommended for the best user experience.

Recommend Setup With Supervisord or Systemd
1. Supervisord  
  a) Setup supervisord config `.venv/bin/python initialize.py -sd`  
  b) Install Supervisord `.venv/bin/pip install supervisor`  
  c) Start Supervisord `supervisord`  

2. Systemd (2 options)  
  Option 1 - Bash script install `sudo bash systemd.sh`  
  Option 2 - [Manual Setup Instructions](https://github.com/cryptosharks131/lndg/blob/master/systemd.md)  
  
Alternatively, you may also make your own task for these files with your preferred tool (task scheduler/cronjob/etc).  

### Notes
1. If you are not using the default settings for LND or you would like to run a LND instance on a network other than `mainnet` you can use the correct flags in step 6 (see `initialize.py --help`) or you can edit the variables directly in `lndg/lndg/settings.py`.  
2. Some systems have a hard time serving static files (docker/macOs) and installing whitenoise and configuring it can help solve this issue. You can use `initialize.py -wn` to setup whitenoise and install it with `.venv/bin/pip install whitenoise`.  
3. If you want to recreate a settings file, delete it from `lndg/lndg/settings.py` and rerun. `initialize.py`  
4. If you plan to run this site continuously, consider setting up a proper web server to host it (see Nginx below).  

### Setup lndg initialize.py options
1. `-ip` or `--nodeip` - Accepts only this host IP to serve the LNDg page - default: `*`
2. `-dir` or `--lnddir` - LND Directory for tls cert and admin macaroon paths - default: `~/.lnd`
3. `-net` or `--network` - Network LND will run over - default: `mainnet`
4. `-server` or `--rpcserver` - Server address to use for rpc communications with LND - default: `localhost:10009`
5. `-sd` or `--supervisord` - Setup supervisord to run jobs/rebalancer background processes - default: `False`
6. `-wn` or `--whitenoise` - Add whitenoise middleware (docker requirement for static files) - default: `False`
7. `-d` or `--docker` - Single option for docker container setup (supervisord + whitenoise) - default: `False`
8. `-dx` or `--debug` - Setup the django site in debug mode - default: `False`

### Updating
1. Make sure you are in the lndg folder `cd lndg`
2. Pull the new files `git pull`
3. Migrate any database changes `.venv/bin/python manage.py migrate`

### Nginx Webserver
If you would like to serve the dashboard at all times, it is recommended to setup a proper production webserver to host the site.  
A bash script has been included to help aide in the setup of a nginx webserver. `sudo bash nginx.sh`

## Key Features
### API Backend
The following data can be accessed at the /api endpoint:  
`payments`  `paymenthops`  `invoices`  `forwards`  `onchain`  `peers`  `channels`  `rebalancer`  `settings`

### Auto-Rebalancer
Here are some notes to help you get started using the auto-rebalancer (AR).
1. The AR variable `AR-Enabled` must be set to 1 (enabled) in order to start looking for new rebalance opportunities.
3. The AR variable `AR-Target%` defines the % size of the channel capacity you would like to use for rebalance attempts.
4. The AR variable `AR-Time` defines the maximum amount of time we will spend looking for a route.
5. The AR variable `AR-MaxFeeRate` defines the maximum amount in ppm a rebalance attempt can ever use for a fee limit.
7. The AR variable `AR-MaxCost%	` defines the maximum % of the ppm being charged on the `INBOUND` receving channel that will be used as the fee limit for the rebalance attempt.
8. Rebalances will only consider any `OUTBOUND` channel that has more outbound liquidity than the current `AR-Outbound%` target and the channel is not currently being targeted as an `INBOUND` receving channel for rebalances.
9. Channels need to be targeted in order to be refilled with outbound liquidity and in order to control costs as a first prioirty, all calculations are based on the specific `INBOUND` receving channel.
10. Enable `INBOUND` receving channels you would like to target and set an inbound liquidity `Target%` on the specific channel. Rebalance attempts will be made until inbound liquidity falls below this channel settting.
11. The `INBOUND` receving channel is the channel that later routes out real payments and earns back the fees paid. Target channels that have lucrative outbound flows.
12. Successful and attempts with only incorrect payment information are tried again immediately.
13. Attempts that fail for other reasons will not be tried again for 30 minutes after the stop time.

## Preview Screens
### Main Dashboard
![image](https://user-images.githubusercontent.com/38626122/138994482-245190b5-a492-4128-bb73-959034ffd879.png)
![image](https://user-images.githubusercontent.com/38626122/137809328-c64c038b-8dbb-40a2-aeb3-a1bae5554d7a.png)
![image](https://user-images.githubusercontent.com/38626122/137809356-ec46193a-478c-424b-a184-2b15cfbb5c52.png)
![image](https://user-images.githubusercontent.com/38626122/137809433-b363fff1-31b6-4b0e-80e9-1916ef0af052.png)
![image](https://user-images.githubusercontent.com/38626122/137809648-bb191ba9-b989-4325-95ac-d25a8333ae62.png)
![image](https://user-images.githubusercontent.com/38626122/137809583-db743233-25c1-4d3e-aaec-2a7767de2c9f.png)

### Peers, Balances, Routes and Pending HTLCs All Open In Separate Screens
![image](https://user-images.githubusercontent.com/38626122/137809809-1ed40cfb-9d12-447a-8e5e-82ae79605895.png)
![image](https://user-images.githubusercontent.com/38626122/137810021-4f69dcb0-5fce-4062-bc49-e75f5dd0feda.png)
![image](https://user-images.githubusercontent.com/38626122/137809882-4a87f86d-290c-456e-9606-ed669fd98561.png)

### Browsable API at `/api` (json format available with url appended with `?format=json`)
![image](https://user-images.githubusercontent.com/38626122/137810278-7f38ac5b-8932-4953-aa4c-9c29d66dce0c.png)

### View Keysend Messages (you can only receive these if you have `accept-keysend=true` in lnd.conf)
![image](https://user-images.githubusercontent.com/38626122/134045287-086d56e3-5959-4f5f-a06e-cb6d2ac4957c.png)

