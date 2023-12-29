# LNDg - GUI for LND Data Analysis and Node Management

Welcome to LNDg, an advanced web interface designed for analyzing LND data and automating node management tasks.

Choose your preferred installation method:

- **1-Click Installation**: Easily install LNDg directly from popular platforms like Umbrel, Citadel, Start9 and RaspiBlitz.
- [Docker Installation](https://github.com/cryptosharks131/lndg#docker-installation-requires-docker-and-docker-compose-be-installed): Ideal for users familiar with Docker and Docker Compose.
- [Manual Installation](https://github.com/cryptosharks131/lndg#manual-installation): If you prefer a hands-on approach to set up LNDg.


## Docker Installation (requires Docker and Docker Compose)

### Prepare Install

```bash
# Clone the repository
git clone https://github.com/cryptosharks131/lndg.git

# Change directory to the repository
cd lndg

# Customize the docker-compose.yaml file
nano docker-compose.yaml
```
**Replace the contents of `docker-compose.yaml` with your desired volume paths and settings. An example configuration is shown below.**
```yaml
services:
  lndg:
    build: .
    volumes:
      - /home/<user>/.lnd:/root/.lnd:ro
      - /home/<user>/<path-to>/lndg/data:/lndg/data:rw
    command:
      - sh
      - -c
      - python initialize.py -net 'mainnet' -server '127.0.0.1:10009' -d && supervisord && python manage.py runserver 0.0.0.0:8889
    network_mode: "host"
```
### Build and Deploy
```bash
# Deploy the Docker image
docker-compose up -d

# Retrieve the admin password for login
nano data/lndg-admin.txt
```
- **This example configuration will host LNDg at http://0.0.0.0:8889. Use the machine IP to reach the LNDg instance.**  
- **Log in to LNDg using the provided password and the username `lndg-admin`.**

### Updating
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# OPTIONAL: remove unused builds and objects
docker system prune -f
```
## Manual Installation

### Step 1 - Install LNDg

1. Clone the repository: `git clone https://github.com/cryptosharks131/lndg.git`
2. Change the directory into the repository: `cd lndg`
3. Ensure you have Python virtualenv installed: `sudo apt install virtualenv`
4. Set up a Python 3 virtual environment: `virtualenv -p python3 .venv`
5. Install the required dependencies: `.venv/bin/pip install -r requirements.txt`
6. Initialize necessary settings for your Django site: `.venv/bin/python initialize.py`
   1. use `.venv/bin/python initialize.py --help` to see additional options
   2. add `-wn | --whitenoise` option to serve static _(.js, .css)_ files (required if installing manually)
      - if **whitenoise** option is provided, you'll need to install it via `.venv/bin/pip install whitenoise`
7. The initial login user is `lndg-admin`, and the password will be genereted and stored in: `data/lndg-admin.txt`
8. Run the server using a Python development server: `.venv/bin/python manage.py runserver 0.0.0.0:8889`

### Step 2 - Setup Backend Controller For Data, Automated Rebalancing, HTLC Stream Data and p2p-trade-secrets

The file `controller.py` orchastrates the services needed to update the backend database with the most up-to-date information, rebalance any channels based on your LNDg dashboard settings, listen for any failure events in your HTLC stream and serves the p2p trade secrets.

**Recommended Setup with Supervisord (least setup) or Systemd (most compatible):**

1. **Systemd (2 options)**
   - Option 1 - Bash script install: `sudo bash systemd.sh`
   - Option 2 - [Manual Setup Instructions](https://github.com/cryptosharks131/lndg/blob/master/systemd.md)

2. **Supervisord**
   - Configure Supervisord by running: `.venv/bin/python initialize.py -sd`
   - Install Supervisord: `.venv/bin/pip install supervisor`
   - Start Supervisord: `supervisord`


Alternatively, you may create your own task for these files using your preferred tool (task scheduler, cron job, etc).

### Updating

1. Make sure you are in the LNDg folder: `cd lndg`
2. Pull the new files from the repository: `git pull`
3. Migrate any database changes: `.venv/bin/python manage.py migrate`

### Notes

1. If you're not using default settings for LND or you'd like to run on a network other than `mainnet`, use the correct flags in step 6 (see `initialize.py --help`) or edit the variables directly in `lndg/settings.py`.
2. You can not run the development server outside of DEBUG mode due to static file issues. To address this, install and configure Whitenoise by running the following command: `.venv/bin/pip install whitenoise && rm lndg/settings.py && .venv/bin/python initialize.py -wn`. (see [6.1](#step-1---install-lndg))
3. You can always update the `lndg/settings.py` file by directly modifying it or re-running the script `.venv/bin/python initialize.py <options> -f`. (see [6](#step-1---install-lndg))
4. If you plan to run this site continuously, it's advisable to set up a proper web server to host it (see Nginx below).
5. You can manage your login credentials from the admin page, accessible at `http:<your-hosting-lndg-ip:port>/lndg-admin`.
6. If you encounter issues accessing the site, ensure that any firewall is open on port 8889, where LNDg is running.

### Using A Webserver
You can serve the dashboard at all times using a webserver instead of the development server. Using a webserver will serve your static files, and installing whitenoise is not required when running in this manner. Any webserver can be used to host the site if configured properly. A bash script has been included to help aid in the setup of an nginx webserver.

To set up the nginx webserver, run the following command:

```bash
sudo bash nginx.sh
```
### When updating
When updating your LNDg installation, follow the same steps as described above. However, after updating, you will also need to restart the uWSGI service to apply the changes to the user interface (UI).

To restart the uWSGI service, use the following command:

```bash
sudo systemctl restart uwsgi.service
``` 

### Postgres
Optionally, you may chose to run LNDg using a postgres database instead of the default sqlite3.

A setup guide can be found here: [Postgres Setup](https://github.com/cryptosharks131/lndg/blob/master/postgres.md)

## Key Features

### Track Peer Events
LNDg will track the changes your peers make to channel policies you have in open channels and any connection events that may happen with those channels.

### Batch Opens
You can use LNDg to batch open up to 10 channels at a time with a single transaction. This can help to significantly reduce the channel open fees incurred when opening multiple channels.

### Watch Tower Management
You can use LNDg to add, monitor, or remove watch towers from the LND node.

### Suggests Fee Rates
LNDg will make suggestions on an adjustment to the current set outbound fee rate for each channel. This uses historical payment and forwarding data over the last 7 days to drive suggestions. You can use the Auto-Fees feature in order to automatically act upon the suggestions given.

You may see another adjustment right after setting the new suggested fee rate on some channels. This is normal, and you should wait ~24 hours before changing the fee rate again on any given channel.

### Suggests New Peers
LNDg will make suggestions for new peers to open channels to based on your node's successful routing history.

#### There are two unique values in LNDg:
1. Volume Score - A score based upon both the count of transactions and the volume of transactions routed through the peer
2. Savings By Volume (ppm) - The amount of sats you could have saved during rebalances if you were peered directly with this node over the total amount routed through the peer

### Channel Performance Metrics
#### LNDg will aggregate your payment and forwarding data to provide the following metrics:
1. Outbound Flow Details - This shows the amount routed outbound next to the amount rebalanced in
2. Revenue Details - This shows the revenue earned on the left, the profit (revenue - cost) in the middle, and the assisted revenue (amount earned due to this channel's inbound flow) on the right
3. Inbound Flow Details - This shows the amount routed inbound next to the amount rebalanced out
4. Updates - This is the number of updates the channel has had and is directly correlated to the space it takes up in channel.db

#### LNDg also provides a P&L page in order to track overall metrics and profitability of the node.

### Password Protected Login
The initial login username is `lndg-admin` but can be easily modified by going to the page found here: `/lndg-admin`

### Suggests AR Actions
LNDg will make suggestions for actions to take around Auto-Rebalancing.

### AR-Autopilot Setting
LNDg will automatically act upon the suggestions it makes on the Suggests AR Actions page.

### HTLC Failure Stream
LNDg will listen for failure events in your htlc stream and record them to the dashboard when they occur.

### API Backend
The following data can be accessed at the /api endpoint:  
`payments`  `paymenthops`  `invoices`  `forwards`  `onchain`  `peers`  `channels`  `rebalancer`  `settings` `pendinghtlcs` `failedhtlcs`

### Peer Reconnection
LNDg will automatically try to resolve any channels that are seen as inactive, no more than every 3 minutes per peer.

## Auto-Fees
### Here are some additional notes to help you get started using Auto-Fees (AF).
LNDg can update your fees on a channel every 24 hours (default) if there is a suggestion listed on the fee rates page. You must make sure the `AF-Enabled` setting is set to `1` and that individual channels you want to be managed are also set to `enabled`. You can view a log of AF changes by opening the Autofees tab.

You can customize some settings of AF by updating the following settings:  
`AF-FailedHTLCs` - The minimum daily failed HTLCs count in which we could trigger a fee increase (depending on flow)  
`AF-Increment` - The increment size of our potential fee changes, all fee suggestions will be a multiple of this value  
`AF-MaxRate` - The maximum fee rate in which we can adjust to  
`AF-MinRate` - The minimum fee rate in which we can adjust to  
`AF-Multiplier` - Multiplier to increase incremental movements, the larger the multiplier, the larger the incremental moves  
`AF-UpdateHours` - Change the number of hours that must pass since the last fee rate change before AF may adjust the fee rate again  
`AF-LowLiqLimit` - The liquidity (%) a channel must drop below before running the `Low Liquidity` fee algorithm  
`AF-ExcessLimit` - The liquidity (%) a channel must go above before running the `Excess Liquidity` fee algorithm  

AF Notes:
1. AF changes only trigger after `AF-UpdateHours` hours of no fee updates via LNDg
2. Channels with less than `AF-LowLiqLimit` outbound liquidty will increase based on failed HTLC counts and incoming flow
3. Channels with more than `AF-ExcessLimit` outbound liquidty will decrease based on no flows or assisted revenues
4. Channels between the previous two groups will increase or decrease based on flow

## Auto-Rebalancer - [Quick Start Guide](https://github.com/cryptosharks131/lndg/blob/master/quickstart.md)
### Here are some additional notes to help you better understand the Auto-Rebalancer (AR).

The objective of the Auto-Rebalancer is to "refill" the liquidity on the local side (i.e. OUTBOUND) of profitable and lucrative channels.  So that, when a forward comes in from another node there is always enough liquidity to route the payment and in return collect the desired routing fees.

1. The AR variable `AR-Enabled` must be set to 1 (enabled) in order to start looking for new rebalance opportunities. (default=0)
2. The AR variable `AR-Target%` defines the % size of the channel capacity you would like to use for rebalance attempts. Example: If a channel size is 1M Sats and AR-Target% = 0.05 LNDg will select an amount of 5% of 1M = 50K for rebalancing. (default=5)
3. The AR variable `AR-Time` defines the maximum amount of time (minutes) we will spend looking for a route. (default=5)
4. The AR variable `AR-MaxFeeRate` defines the maximum amount in ppm a rebalance attempt can ever use for a fee limit. This is the maximum limit to ensure the total fee does not exceed this amount. Example: AR-MaxFeeRate = 800 will ensure the rebalance fee is always less than 800 ppm. (default=100)
5. The AR variable `AR-MaxCost%	` defines the maximum % of the ppm being charged on the `INBOUND` receving channel that will be used as the fee limit for the rebalance attempt. Example: If your fee to node A is 1000ppm and AR-MaxCost% = 0.5 LNDg will use 50% of 1000ppm = 500ppm max fee limit for rebalancing. (default=65)
6. The AR variable `AR-Outbound%` helps identify all the channels that would be a candidate for rebalancing targetd channels. Rebalances will only consider any `OUTBOUND` channel that has more outbound liquidity than the current `AR-Outbound%` setting AND the channel is not currently being targeted as an `INBOUND` receving channel for rebalances.  Example: AR-Outboud% = 0.6 would make all channels with an outbound capacity of 60% or more AND not enabled under AR on the channel line to be a candidate for rebalancing. (default=75)
7. Channels need to be targeted in order to be refilled with outbound liquidity and in order to control costs as a first prioirty, all calculations are based on the specific `INBOUND` receving channel.
8. Enable `INBOUND` receving channels you would like to target and set an inbound liquidity `Target%` on the specific channel. Rebalance attempts will be made until inbound liquidity falls below this channel settting.
9. The `INBOUND` receving channel is the channel that later routes out real payments and earns back the fees paid. Target channels that have lucrative outbound flows.
10. Attempts that are successful or attempts with only incorrect payment information are tried again immediately. Example: If a rebalancing for 50k was sucessful, AR will try another 50k immediately with the same parameters.
11. Attempts that fail for other reasons will not be tried again for 30 minutes after the stop time. This allows the liquidity in the network to move around for 30 mins before trying another rebalancing attempt that previously failed. The 30 minute window can be customized by updating the `AR-WaitPeriod` setting.

Additional customization options:
1. `AR-Autopilot` - Automatically act upon suggestions on the AR Actions page. (default=0)
2. `AR-WaitPeriod` - How much time (minutes) AR should wait before scheduling a channel that has recently failed an attempt. (default=30)
3. `AR-Variance` - How much to randomly vary the target rebalance amount by this % of the target amount.  (default=0)
4. `AR-Inbound%` - The default `iTarget%` value to assign to new channels.  (default=100)
5. `AR-APDays` - The number of days of historical data AP should use to decide actions to take. (default=7)
6. `AR-Workers` - Define how many parallel rebalances to spin up at once. (default=1)

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
  Target Time (min): 3
  Target Outbound Above (%): 0.4
  Global Max Fee Rate (ppm): 500
  Max Cost (%): 0.6
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

### Channel Performance, Peers, Balances, Routes, Keysends and Pending HTLCs All Open In Separate Screens
![image](https://user-images.githubusercontent.com/38626122/150556928-bb8772fb-14c4-4b7a-865e-a8350aac7f83.png)
![image](https://user-images.githubusercontent.com/38626122/137809809-1ed40cfb-9d12-447a-8e5e-82ae79605895.png)
![image](https://user-images.githubusercontent.com/38626122/137810021-4f69dcb0-5fce-4062-bc49-e75f5dd0feda.png)
![image](https://user-images.githubusercontent.com/38626122/137809882-4a87f86d-290c-456e-9606-ed669fd98561.png)
![image](https://user-images.githubusercontent.com/38626122/148699417-bd9fbb49-72f5-4c3f-811f-e18c990a06ba.png)

### Manage Auto-Fees Or Get Suggestions
![image](https://user-images.githubusercontent.com/38626122/175364451-a7e2bc62-71bd-4a2d-99f6-6a1f27e5999a.png)

### Batch Open Channels
![image](https://user-images.githubusercontent.com/38626122/175364599-ac894b68-a11d-420b-93b3-3ee8dffc857f.png)

### Suggests Peers To Open With and Rebalancer Actions To Take
![image](https://user-images.githubusercontent.com/38626122/148699445-88efeacd-3cfc-429c-91d8-3a52ee633195.png)
![image](https://user-images.githubusercontent.com/38626122/148699467-62ebbd7d-9f36-4707-88fd-62f2cc2a5506.png)

### Browsable API at `/api` (json format available with url appended with `?format=json`)
![image](https://user-images.githubusercontent.com/38626122/137810278-7f38ac5b-8932-4953-aa4c-9c29d66dce0c.png)

### View Keysend Messages (you can only receive these if you have `accept-keysend=true` in lnd.conf)
![image](https://user-images.githubusercontent.com/38626122/134045287-086d56e3-5959-4f5f-a06e-cb6d2ac4957c.png)

