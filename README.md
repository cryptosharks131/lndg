# LNDg
Lite GUI web interface to analyze lnd data and manage your node with automation.

Start by choosing one of the following installation methods:  
[Docker Installation](https://github.com/cryptosharks131/lndg#docker-installation-requires-docker-and-docker-compose-be-installed) | [Umbrel Installation](https://github.com/cryptosharks131/lndg#umbrel-installation) | [Manual Installation](https://github.com/cryptosharks131/lndg#manual-installation)

## Docker Installation (requires docker and docker-compose be installed)
### Build and deploy
1. Clone respository `git clone https://github.com/cryptosharks131/lndg.git`
2. Change directory into the repo `cd lndg`
3. Initialize db and admin backup `touch db.sqlite3 && touch lndg-admin.txt`
4. Update `docker-compose.yaml` if you are a non-root user and then build/deploy your docker image: `docker-compose up -d`
5. LNDg should now be available on port `8889`
6. Open and copy the password from output file: `nano lndg-admin.txt`
7. Use the password from the output file and the username `lndg-admin` to login

### Updating
```
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Umbrel Installation
### Build and deploy
1. Log into your umbrel via ssh
2. Clone respository `git clone https://github.com/cryptosharks131/lndg.git`
3. Change directory `cd lndg`
4. Initialize db and admin backup `touch db.sqlite3 && touch lndg-admin.txt`
5. Copy and replace the contents of the docker-compose.yaml with the below: `nano docker-compose.yaml`
```
services:
  lndg:
    build: .
    volumes:
      - /home/umbrel/umbrel/lnd:/root/.lnd:ro
      - /home/umbrel/lndg/db.sqlite3:/lndg/db.sqlite3:rw
      - /home/umbrel/lndg/lndg-admin.txt:/lndg/lndg-admin.txt:rw
    command:
      - sh
      - -c
      - python initialize.py -net 'mainnet' -server '10.21.21.9:10009' -d && supervisord && python manage.py runserver 0.0.0.0:8000
    ports:
      - 8889:8000
networks: 
  default: 
    external: true
    name: umbrel_main_network
```
5. Deploy your docker image: `docker-compose up -d`
6. You can now access LNDg via your browser on port 8889: `http://umbrel.local:8889`
7. Open and copy the password from output file: `nano lndg-admin.txt`
8. Use the password from the output file and the username `lndg-admin` to login

### Updating
```
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Manual Installation
### Step 1 - Install lndg
1. Clone respository `git clone https://github.com/cryptosharks131/lndg.git`
2. Change directory into the repo `cd lndg`
3. Make sure you have python virtualenv installed `apt install virtualenv`
4. Setup a python3 virtual environment `virtualenv -p python3 .venv`
5. Install required dependencies `.venv/bin/pip install -r requirements.txt`
6. Initialize some settings for your django site (see notes below) `.venv/bin/python initialize.py`
7. The initial login user is `lndg-admin` and the password is output here: `lndg-admin.txt`
8. Generate some initial data for your dashboard `.venv/bin/python jobs.py`
9. Run the server via a python development server `.venv/bin/python manage.py runserver 0.0.0.0:8889`  
Tip: If you plan to only use the development server, you will need to setup whitenoise (see note below).  

### Step 2 - Setup Backend Data, Automated Rebalancing and HTLC Stream Data
The files `jobs.py`, `rebalancer.py` and `htlc_stream.py` inside lndg/gui/ serve to update the backend database with the most up to date information, rebalance any channels based on your lndg dashboard settings and to listen for any failure events in your htlc stream. A refresh interval of at least 10-20 seconds is recommended for the `jobs.py` and `rebalancer.py` files for the best user experience.

Recommend Setup With Supervisord or Systemd
1. Supervisord  
  a) Setup supervisord config `.venv/bin/python initialize.py -sd`  
  b) Install Supervisord `.venv/bin/pip install supervisor`  
  c) Start Supervisord `supervisord`  

2. Systemd (2 options)  
  Option 1 - Bash script install `sudo bash systemd.sh`  
  Option 2 - [Manual Setup Instructions](https://github.com/cryptosharks131/lndg/blob/master/systemd.md)  
  
Alternatively, you may also make your own task for these files with your preferred tool (task scheduler/cronjob/etc).  

### Updating
1. Make sure you are in the lndg folder `cd lndg`
2. Pull the new files `git pull`
3. Migrate any database changes `.venv/bin/python manage.py migrate`

### Notes
1. If you are not using the default settings for LND or you would like to run a LND instance on a network other than `mainnet` you can use the correct flags in step 6 (see `initialize.py --help`) or you can edit the variables directly in `lndg/lndg/settings.py`.  
2. Some systems have a hard time serving static files (docker/macOs) and installing whitenoise and configuring it can help solve this issue. You can use `initialize.py -wn` to setup whitenoise and install it with `.venv/bin/pip install whitenoise`.  
3. If you want to recreate a settings file, delete it from `lndg/lndg/settings.py` and rerun. `initialize.py`  
4. If you plan to run this site continuously, consider setting up a proper web server to host it (see Nginx below). 
5. You can manage your login credentials from the admin page. Example: `lndg.local/lndg-admin` 
6. If you have issues reaching the site, verify the firewall is open on port 8889 where LNDg is running

### Setup lndg initialize.py options
1. `-ip` or `--nodeip` - Accepts only this host IP to serve the LNDg page - default: `*`
2. `-dir` or `--lnddir` - LND Directory for tls cert and admin macaroon paths - default: `~/.lnd`
3. `-net` or `--network` - Network LND will run over - default: `mainnet`
4. `-server` or `--rpcserver` - Server address to use for rpc communications with LND - default: `localhost:10009`
5. `-sd` or `--supervisord` - Setup supervisord to run jobs/rebalancer background processes - default: `False`
6. `-sdu` or `--sduser` - Configure supervisord with a non-root user - default: `root`
7. `-wn` or `--whitenoise` - Add whitenoise middleware (docker requirement for static files) - default: `False`
8. `-d` or `--docker` - Single option for docker container setup (supervisord + whitenoise) - default: `False`
9. `-dx` or `--debug` - Setup the django site in debug mode - default: `False`
10. `-pw` or `--adminpw` Setup a custom admin password - default: `Randomized`

### Using A Webserver
You can serve the dashboard at all times using a webserver instead of the development server.  Using a webserver will serve your static files and installing whitenoise is not required when running in this manner. Any webserver can be used to host the site if configured properly. A bash script has been included to help aide in the setup of a nginx webserver. `sudo bash nginx.sh`

## Key Features
### API Backend
The following data can be accessed at the /api endpoint:  
`payments`  `paymenthops`  `invoices`  `forwards`  `onchain`  `peers`  `channels`  `rebalancer`  `settings` `pendinghtlcs` `failedhtlcs`

### Peer Reconnection
LNDg will automatically try to resolve any channels that are seen as inactive, no more than every 3 minutes per peer.

### Suggests New Peers
LNDg will make suggestions for new peers to open channels to based on your node's successful routing history.

### Suggests AR Actions
LNDg will make suggestions for actions to take around Auto-Rebalancing.

### HTLC Failure Stream
LNDg will listen for failure events in your htlc stream and record them to the dashboard when they occur.

### Auto-Rebalancer
Here are some notes to help you get started using the Auto-Rebalancer (AR).

The objective of the Auto-Rebalancer is to "refill" the liquidity on the local side (i.e. OUTBOUND) of profitable and lucarative channels.  So that, when a forward comes in from another node there is always enough liquidity to route the payment and in return collect the desired routing fees.

1. The AR variable `AR-Enabled` must be set to 1 (enabled) in order to start looking for new rebalance opportunities.
2. The AR variable `AR-Target%` defines the % size of the channel capacity you would like to use for rebalance attempts. Example: If a channel size is 1M Sats and AR-Target% = 0.05 LNDg will select an amount of 5% of 1M = 50K for rebalancing.
3. The AR variable `AR-Time` defines the maximum amount of time we will spend looking for a route. Example: 5 minutes
4. The AR variable `AR-MaxFeeRate` defines the maximum amount in ppm a rebalance attempt can ever use for a fee limit. This is the maximum limit to ensure the total fee does not exceed this amount. Example: AR-MaxFeeRate = 800 will ensure the rebalance fee is always less than 800 ppm.
5. The AR variable `AR-MaxCost%	` defines the maximum % of the ppm being charged on the `INBOUND` receving channel that will be used as the fee limit for the rebalance attempt. Example: If your fee to node A is 1000ppm and AR-MaxCost% = 0.5 LNDg will use 50% of 1000ppm = 500ppm max fee limit for rebalancing.
6. The AR variable `AR-Outbound%` helps identify all the channels that would be a candidate for rebalancing targetd channels. Rebalances will only consider any `OUTBOUND` channel that has more outbound liquidity than the current `AR-Outbound%` setting AND the channel is not currently being targeted as an `INBOUND` receving channel for rebalances.  Example: AR-Outboud% = 0.6 would make all channels with an outbound capacity of 60% or more AND not enabled under AR on the channel line to be a candidate for rebalancing. 
7. Channels need to be targeted in order to be refilled with outbound liquidity and in order to control costs as a first prioirty, all calculations are based on the specific `INBOUND` receving channel.
8. Enable `INBOUND` receving channels you would like to target and set an inbound liquidity `Target%` on the specific channel. Rebalance attempts will be made until inbound liquidity falls below this channel settting.
9. The `INBOUND` receving channel is the channel that later routes out real payments and earns back the fees paid. Target channels that have lucrative outbound flows.
10. Attempts that are successful or attempts with only incorrect payment information are tried again immediately. Example: If a rebalancing for 50k was sucessful, AR will try another 50k immediately with the same parameters.
11. Attempts that fail for other reasons will not be tried again for 30 minutes after the stop time. This allows the liquidity in the network to move around for 30 mins before trying another rebalancing attempt that previously failed.

#### Steps to start the Auto-Rebalancer:
1. Update Channel Specific Settings  
  a. Go to Active Channels section  
  b. Find the channels you would like to activate for rebalancing (this refills its outbound)  
  c. On far right column Click the Enable button to activate rebalancing  
  d. The dashboard will refresh and show AR-Target 100%  
  e. Adjust the AR-Target to desired % of liquidity you want to keep on remote INBOUND side. Example select 0.60 if you want 60% of the channel capacity on Remote/INBOUND side  which would mean that there is 40% on Local/OUTBOUND side  
  f. Hit Enter  
  g. Dashboard will refresh in the browser  
  h. Make sure you enable all channels that are valuable outbound routes for you to ensure they are not used for filling up routes you have targeted (you can enable and target 100% in order to avoid any action on this channel from the rebalancer)  

2. Update Global Settings  
  a. Go to section Update Auto Rebalancer Settings  
  b. Select the global settings (sample below):  
  c. Click OK button to submit  
  d. Once enabled is set to 1 in the global settings - the rebalancer will become active
  ```
  Enabled: 1
  Target Amount (%): 0.03
  Target Time (min): 5
  Target Outbound Above (%): 0.4
  Global Max Fee Rate (ppm): 200
  Max Cost (%): 0.5
  ```
3. Go to section Last 10 Rebalance Requests - that will show the list of the rebalancing queue and status.  

If you want a channel not to be picked for rebalancing (i.e. it is already full with OUTBOUND capacity that you desire), enable the channel and set the AR-Target% to 100. The rebalancer will ignore the channel while selecting the channels for outbound candidates and since its INBOUND can never be above 100% it will never trigger a rebalance.  

## Preview Screens
### Main Dashboard
![image](https://user-images.githubusercontent.com/38626122/148699177-d10d412e-641e-4676-acac-2047e7e2d7a6.png)
![image](https://user-images.githubusercontent.com/38626122/148699209-667936fd-c56f-484f-8dd4-75e052c8c14f.png)
![image](https://user-images.githubusercontent.com/38626122/148699224-efb70fcf-0b7e-45cf-bd98-de833b2cff88.png)
![image](https://user-images.githubusercontent.com/38626122/148699273-be470d86-e76c-4935-8337-2b9737aed73e.png)
![image](https://user-images.githubusercontent.com/38626122/148699286-0b1d2c13-191a-4c6c-99ae-ce3d8b8ac64d.png)
![image](https://user-images.githubusercontent.com/38626122/137809583-db743233-25c1-4d3e-aaec-2a7767de2c9f.png)

### Peers, Balances, Routes, Keysends and Pending HTLCs All Open In Separate Screens
![image](https://user-images.githubusercontent.com/38626122/137809809-1ed40cfb-9d12-447a-8e5e-82ae79605895.png)
![image](https://user-images.githubusercontent.com/38626122/137810021-4f69dcb0-5fce-4062-bc49-e75f5dd0feda.png)
![image](https://user-images.githubusercontent.com/38626122/137809882-4a87f86d-290c-456e-9606-ed669fd98561.png)
![image](https://user-images.githubusercontent.com/38626122/148699417-bd9fbb49-72f5-4c3f-811f-e18c990a06ba.png)

### Suggests Peers To Open With and Rebalancer Actions To Take
![image](https://user-images.githubusercontent.com/38626122/148699445-88efeacd-3cfc-429c-91d8-3a52ee633195.png)
![image](https://user-images.githubusercontent.com/38626122/148699467-62ebbd7d-9f36-4707-88fd-62f2cc2a5506.png)

### Browsable API at `/api` (json format available with url appended with `?format=json`)
![image](https://user-images.githubusercontent.com/38626122/137810278-7f38ac5b-8932-4953-aa4c-9c29d66dce0c.png)

### View Keysend Messages (you can only receive these if you have `accept-keysend=true` in lnd.conf)
![image](https://user-images.githubusercontent.com/38626122/134045287-086d56e3-5959-4f5f-a06e-cb6d2ac4957c.png)

