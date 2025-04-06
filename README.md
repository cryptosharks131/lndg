# LNDg - GUI for LND Data Analysis and Node Management

Welcome to LNDg, an advanced web interface designed for analyzing Lightning Network Daemon (LND) data and automating node management tasks.

## Table of Contents

- [Installation](#installation)
  - [1-Click Installation](#1-click-installation)
  - [Docker Installation](#docker-installation)
  - [Manual Installation](#manual-installation)
- [Updating LNDg](#updating-lndg)
  - [Docker Update](#docker-update)
  - [Manual Update](#manual-update)
- [Configuration](#configuration)
  - [Backend Controller Setup](#backend-controller-setup)
  - [Webserver Setup (Optional)](#webserver-setup-optional)
  - [PostgreSQL Setup (Optional)](#postgresql-setup-optional)
  - [Important Notes](#important-notes)
- [Key Features](#key-features)
  - [Track Peer Events](#track-peer-events)
  - [Batch Channel Opens](#batch-channel-opens)
  - [Watch Tower Management](#watch-tower-management)
  - [Fee Rate Suggestions](#fee-rate-suggestions)
  - [New Peer Suggestions](#new-peer-suggestions)
  - [Channel Performance Metrics](#channel-performance-metrics)
  - [Password Protected Login](#password-protected-login)
  - [Auto-Rebalance Action Suggestions](#auto-rebalance-action-suggestions)
  - [AR-Autopilot Setting](#ar-autopilot-setting)
  - [HTLC Failure Stream](#htlc-failure-stream)
  - [API Backend](#api-backend)
  - [Peer Reconnection](#peer-reconnection)
- [Auto-Fees](#auto-fees)
  - [Auto-Fees Settings](#auto-fees-settings)
  - [Auto-Fees Notes](#auto-fees-notes)
- [Auto-Rebalancer](#auto-rebalancer)
  - [Understanding Auto-Rebalancer](#understanding-auto-rebalancer)
  - [Auto-Rebalancer Settings](#auto-rebalancer-settings)
  - [Additional Customization Options](#additional-customization-options)
  - [Steps to Start the Auto-Rebalancer](#steps-to-start-the-auto-rebalancer)
- [Preview Screens](#preview-screens)

## Installation

Choose your preferred installation method:

### 1-Click Installation

Easily install LNDg directly from popular platforms like Umbrel, Citadel, Start9, and RaspiBlitz. Follow the instructions provided by your chosen platform.

### Docker Installation

This method requires Docker and Docker Compose to be installed on your system.

**1. Prepare Installation:**

```bash
# Clone the repository
git clone https://github.com/cryptosharks131/lndg.git

# Change directory to the repository
cd lndg

# Customize the docker-compose.yaml file
nano docker-compose.yaml
```

Replace the contents of `docker-compose.yaml` with your desired volume paths and settings. An example configuration is shown below:

```yaml
services:
  lndg:
    build: .
    volumes:
      # Adjust paths according to your setup
      - /home/<user>/.lnd:/root/.lnd:ro
      - /home/<user>/<path-to>/lndg/data:/app/data:rw
    command:
      - sh
      - -c
      # Customize network ('mainnet' or 'testnet') and RPC address/port if needed
      - python initialize.py -net 'mainnet' -rpc '127.0.0.1:10009' -wn && python controller.py runserver 0.0.0.0:8889 > /var/log/lndg-controller.log 2>&1
    # Use host network mode for simplicity, adjust if needed
    network_mode: "host"
```

**2. Build and Deploy:**

```bash
# Build and deploy the Docker container in detached mode
docker-compose up -d

# Retrieve the admin password for the initial login
cat data/lndg-admin.txt
```

- This example configuration will host LNDg at `http://<your-machine-ip>:8889`.
- Log in to LNDg using the username `lndg-admin` and the password retrieved from `data/lndg-admin.txt`.

### Manual Installation

This method provides a hands-on approach to setting up LNDg.

**1. Install LNDg:**

```bash
# Clone the repository
git clone https://github.com/cryptosharks131/lndg.git

# Change directory
cd lndg

# Ensure Python virtualenv is installed (example for Debian/Ubuntu)
sudo apt update && sudo apt install -y virtualenv

# Set up a Python 3 virtual environment
virtualenv -p python3 .venv

# Install required dependencies
.venv/bin/pip install -r requirements.txt

# Initialize settings (use --help for options)
# Add -wn or --whitenoise to serve static files if not using a separate webserver
.venv/bin/python initialize.py -wn

# Install whitenoise if the -wn flag was used
.venv/bin/pip install whitenoise

# Retrieve the admin password
cat data/lndg-admin.txt

# Run the development server (adjust IP/port if needed)
.venv/bin/python manage.py runserver 0.0.0.0:8889
```

- The initial login user is `lndg-admin`. The password is in `data/lndg-admin.txt`.
- Access LNDg at `http://<your-machine-ip>:8889`.

**2. Setup Backend Controller:**

The `controller.py` script manages backend database updates, automated rebalancing, HTLC stream data, and p2p trade secrets. Set it up to run persistently using `systemd` (recommended) or `supervisord`.

- **Systemd:**
  - Option 1 (Script): `sudo bash systemd.sh`
  - Option 2 (Manual): [Manual Systemd Setup Instructions](https://github.com/cryptosharks131/lndg/blob/master/systemd.md)

- **Supervisord:**
  - Configure Supervisord: `.venv/bin/python initialize.py -sd`
  - Install Supervisord: `.venv/bin/pip install supervisor`
  - Start Supervisord: `supervisord`

Alternatively, use your preferred task scheduler (like `cron`) to run `controller.py`.

## Updating LNDg

### Docker Update

```bash
# Navigate to the lndg directory
cd lndg

# Stop the current containers
docker-compose down

# Rebuild the image without using cache
docker-compose build --no-cache

# Start the updated containers
docker-compose up -d

# OPTIONAL: Remove unused Docker objects
docker system prune -f
```

### Manual Update

```bash
# Navigate to the lndg directory
cd lndg

# Pull the latest changes
git pull

# Install any new dependencies
.venv/bin/pip install -r requirements.txt

# Apply any database migrations
.venv/bin/python manage.py migrate

# Restart the LNDg service (web server and controller)
# Example for systemd:
# sudo systemctl restart lndg-web.service
# sudo systemctl restart lndg-controller.service
# If using supervisord:
# supervisorctl restart lndg-web
# supervisorctl restart lndg-controller
# If using the development server, stop and restart it:
# .venv/bin/python manage.py runserver 0.0.0.0:8889
```

If using a webserver like Nginx with uWSGI (see below), restart the uWSGI service:

```bash
sudo systemctl restart uwsgi.service
``` 

## Configuration

### Backend Controller Setup

As mentioned in the [Manual Installation](#manual-installation), the `controller.py` needs to run persistently. Use `systemd` or `supervisord` for reliable operation.

### Webserver Setup (Optional)

For continuous operation and better performance, especially in non-DEBUG mode, use a dedicated webserver like Nginx instead of the Django development server. Using a webserver also handles static file serving, making the `whitenoise` dependency optional.

A helper script is included for setting up Nginx:

```bash
sudo bash nginx.sh
```

Remember to restart the `uwsgi.service` after updates if using this setup.

### PostgreSQL Setup (Optional)

LNDg uses SQLite3 by default. You can configure it to use a PostgreSQL database for potentially better performance in high-usage scenarios.

See the [Postgres Setup Guide](https://github.com/cryptosharks131/lndg/blob/master/postgres.md) for instructions.

### Important Notes

1.  **Custom LND Settings:** If not using default LND settings (e.g., non-default ports, network), use flags during `initialize.py` (check `--help`) or edit `lndg/settings.py` directly.
2.  **Static Files (Manual Install):** If running manually *without* a separate webserver (like Nginx), you MUST use the `-wn` flag with `initialize.py` and install `whitenoise` to serve static files (.css, .js). Running the development server (`manage.py runserver`) with `DEBUG=False` without `whitenoise` or a webserver will cause issues.
3.  **Updating Settings:** Modify `lndg/settings.py` directly or re-run `initialize.py <options> -f` to update settings.
4.  **Admin Credentials:** Manage login credentials via the admin interface at `http://<your-lndg-ip:port>/lndg-admin`.
5.  **Firewall:** Ensure your firewall allows incoming connections on the port LNDg is running on (default: 8889).

## Key Features

### Track Peer Events

Monitor changes your peers make to channel policies and track connection events for your open channels.

### Batch Channel Opens

Open up to 10 channels simultaneously in a single transaction, potentially reducing on-chain fees.

### Watch Tower Management

Add, monitor, and remove watchtowers connected to your LND node.

### Fee Rate Suggestions

Receive suggestions for adjusting outbound fee rates based on the last 7 days of payment and forwarding data. Enable Auto-Fees to act on these suggestions automatically. Note: Allow ~24 hours after a manual change before making another adjustment on the same channel.

### New Peer Suggestions

Get recommendations for new peers based on your node's successful routing history, considering:
- **Volume Score:** Based on the count and volume of transactions routed through the peer.
- **Savings By Volume (ppm):** Estimated sats saved on rebalances if peered directly, relative to the volume routed through the peer.

### Channel Performance Metrics

Aggregate payment and forwarding data provides:
1.  **Outbound Flow:** Amount routed outbound vs. amount rebalanced in.
2.  **Revenue:** Total earned, profit (revenue - cost), and assisted revenue (earned due to this channel's inbound).
3.  **Inbound Flow:** Amount routed inbound vs. amount rebalanced out.
4.  **Updates:** Number of channel updates (correlates to `channel.db` size).

A dedicated P&L page tracks overall node metrics and profitability.

### Password Protected Login

Initial username is `lndg-admin`. Change it via the `/lndg-admin` page.

### Auto-Rebalance Action Suggestions

LNDg suggests actions to optimize Auto-Rebalancing (AR).

### AR-Autopilot Setting

Enable this setting (`AR-Autopilot`) to automatically implement the suggestions from the AR Actions page.

### HTLC Failure Stream

Listen for and record HTLC failure events to the dashboard.

### API Backend

Access data programmatically via the `/api` endpoint. Available resources include:
`payments`, `paymenthops`, `invoices`, `forwards`, `onchain`, `peers`, `channels`, `rebalancer`, `settings`, `pendinghtlcs`, `failedhtlcs`.
Append `?format=json` for JSON output.

### Peer Reconnection

Automatically attempts to reconnect to peers associated with inactive channels (max once every 3 minutes per peer).

## Auto-Fees

LNDg can automatically update channel fees based on performance suggestions.

### Auto-Fees Settings

Customize Auto-Fees (AF) behavior via the settings page:
- `AF-Enabled`: Set to `1` to enable Auto-Fees globally. Individual channels must also be enabled.
- `AF-FailedHTLCs`: Minimum daily failed HTLC count to potentially trigger a fee increase (based on flow).
- `AF-Increment`: Base increment size (ppm) for fee changes. Suggestions are multiples of this value.
- `AF-MaxRate`: Maximum fee rate (ppm) AF can set.
- `AF-MinRate`: Minimum fee rate (ppm) AF can set.
- `AF-Multiplier`: Multiplies the `AF-Increment` for larger fee adjustments.
- `AF-UpdateHours`: Minimum hours between AF adjustments for a single channel (default: 24).
- `AF-LowLiqLimit`: Outbound liquidity (%) threshold below which the "Low Liquidity" fee algorithm applies.
- `AF-ExcessLimit`: Outbound liquidity (%) threshold above which the "Excess Liquidity" fee algorithm applies.

### Auto-Fees Notes

1.  AF adjustments occur only if `AF-UpdateHours` have passed since the last LNDg fee update for that channel.
2.  Channels below `AF-LowLiqLimit`% outbound liquidity may see fee increases based on failed HTLCs and incoming flow.
3.  Channels above `AF-ExcessLimit`% outbound liquidity may see fee decreases based on lack of flow or assisted revenue.
4.  Channels between these limits adjust based on overall flow patterns.
5.  View AF change history in the "Autofees" tab.

## Auto-Rebalancer

Automatically manage channel liquidity to maintain outbound capacity on profitable routes. See the [Quick Start Guide](https://github.com/cryptosharks131/lndg/blob/master/quickstart.md).

### Understanding Auto-Rebalancer

The goal is to move funds (rebalance) *into* the local side (outbound capacity) of channels that frequently route payments *out* successfully. This ensures liquidity is available to earn routing fees.

### Auto-Rebalancer Settings

Configure Auto-Rebalancer (AR) globally:
- `AR-Enabled`: Set to `1` to activate AR (default: 0).
- `AR-Target%`: Default rebalance amount as a percentage of channel capacity (e.g., 0.05 means 5%). Used if not set per-channel (default: 5).
- `AR-Time`: Maximum time (minutes) to search for a rebalance route (default: 5).
- `AR-MaxFeeRate`: Absolute maximum fee rate (ppm) allowed for any rebalance attempt (default: 100).
- `AR-MaxCost%`: Maximum rebalance fee limit as a percentage of the *target inbound channel's* current outbound fee rate (e.g., 0.65 means 65%) (default: 65).
- `AR-Outbound%`: Channels with *more* outbound liquidity than this percentage are considered potential *sources* for rebalancing funds *from* (default: 75). They must also *not* be targeted for receiving inbound liquidity.

### Additional Customization Options

- `AR-Autopilot`: Set to `1` to automatically act on AR suggestions (default: 0).
- `AR-WaitPeriod`: Time (minutes) to wait before retrying a rebalance on a channel after a failure (default: 30).
- `AR-Variance`: Randomly vary the target rebalance amount by this percentage (default: 0).
- `AR-Inbound%`: Default inbound target (`iTarget%`) for newly monitored channels (default: 100).
- `AR-APDays`: Number of days of historical data for Autopilot decisions (default: 7).
- `AR-Workers`: Number of parallel rebalance attempts to run concurrently (default: 1).

### Steps to Start the Auto-Rebalancer

1.  **Configure Target Channels (Receiving Inbound Liquidity):**
    a. Go to the "Active Channels" section on the LNDg dashboard.
    b. Identify channels you want to *refill* with outbound liquidity (these are your profitable outbound routes).
    c. Click the "Enable" button in the far-right column for these target channels.
    d. The page will refresh, showing `AR-Target: 100%`.
    e. Adjust the `AR-Target` percentage for each channel. This represents the desired *remote* (inbound) liquidity percentage. E.g., `0.60` means you want 60% inbound / 40% outbound liquidity. Press Enter to save.
    f. **Important:** Enable *all* channels valuable for outbound routing, even if you don't actively target them for refilling. Set their `AR-Target` to `100%` to prevent AR from using them as a *source* for rebalancing funds *away* from them.

2.  **Update Global Settings:**
    a. Go to the "Update Auto Rebalancer Settings" section.
    b. Set `Enabled: 1` to activate the rebalancer.
    c. Configure other global settings (`Target Amount (%)`, `Target Time (min)`, `Target Outbound Above (%)`, `Global Max Fee Rate (ppm)`, `Max Cost (%)`) as needed.
    d. Click "OK" to submit.

3.  **Monitor Rebalances:**
    a. Check the "Last 10 Rebalance Requests" section to view the queue and status of attempts.

**Notes on AR Logic:**
- Rebalances aim to decrease inbound liquidity below the channel-specific `AR-Target%`.
- Channels with outbound liquidity *above* the global `AR-Outbound%` are potential *sources* to push funds from, *unless* they are themselves enabled with an `AR-Target`.
- Successful attempts or failures due to incorrect payment info are retried immediately.
- Other failures trigger a wait period (`AR-WaitPeriod`) before retrying on that channel.

## Preview Screens

### Main Dashboard
![image](https://user-images.githubusercontent.com/38626122/148699177-d10d412e-641e-4676-acac-2047e7e2d7a6.png)
![image](https://user-images.githubusercontent.com/38626122/148699209-667936fd-c56f-484f-8dd4-75e052c8c14f.png)
![image](https://user-images.githubusercontent.com/38626122/148699224-efb70fcf-0b7e-45cf-bd98-de833b2cff88.png)
![image](https://user-images.githubusercontent.com/38626122/148699273-be470d86-e76c-4935-8337-2b9737aed73e.png)
![image](https://user-images.githubusercontent.com/38626122/148699286-0b1d2c13-191a-4c6c-99ae-ce3d8b8ac64d.png)
![image](https://user-images.githubusercontent.com/38626122/137809583-db743233-25c1-4d3e-aaec-2a7767de2c9f.png)

### Separate Screens (Performance, Peers, Balances, etc.)
![image](https://user-images.githubusercontent.com/38626122/150556928-bb8772fb-14c4-4b7a-865e-a8350aac7f83.png)
![image](https://user-images.githubusercontent.com/38626122/137809809-1ed40cfb-9d12-447a-8e5e-82ae79605895.png)
![image](https://user-images.githubusercontent.com/38626122/137810021-4f69dcb0-5fce-4062-bc49-e75f5dd0feda.png)
![image](https://user-images.githubusercontent.com/38626122/137809882-4a87f86d-290c-456e-9606-ed669fd98561.png)
![image](https://user-images.githubusercontent.com/38626122/148699417-bd9fbb49-72f5-4c3f-811f-e18c990a06ba.png)

### Manage Auto-Fees / Get Suggestions
![image](https://user-images.githubusercontent.com/38626122/175364451-a7e2bc62-71bd-4a2d-99f6-6a1f27e5999a.png)

### Batch Open Channels
![image](https://user-images.githubusercontent.com/38626122/175364599-ac894b68-a11d-420b-93b3-3ee8dffc857f.png)

### Suggestions (Peers, Rebalancer Actions)
![image](https://user-images.githubusercontent.com/38626122/148699445-88efeacd-3cfc-429c-91d8-3a52ee633195.png)
![image](https://user-images.githubusercontent.com/38626122/148699467-62ebbd7d-9f36-4707-88fd-62f2cc2a5506.png)

### API Browser (`/api`)
![image](https://user-images.githubusercontent.com/38626122/137810278-7f38ac5b-8932-4953-aa4c-9c29d66dce0c.png)

### View Keysend Messages
*(Requires `accept-keysend=true` in lnd.conf)*

![image](https://user-images.githubusercontent.com/38626122/134045287-086d56e3-5959-4f5f-a06e-cb6d2ac4957c.png)

