# Systemd Setup For Backend Refreshes And Rebalancer Tools

You will need to fill in the proper username below in the paths marked `<run_as_user>`. This assumes you have installed lndg on the home directory of the user. For example, user `mynode` will have a home directory of `/home/mynode/`.

## Backend Refreshes
Create a simple bash file to call `jobs.py`, copying the contents below to the file.  
`nano /home/<run_as_user>/lndg/jobs.sh`
```
#!/bin/bash

/home/<run_as_user>/lndg/.venv/bin/python /home/<run_as_user>/lndg/jobs.py
```
Create a service file for `jobs.py`, copying the contents below to the file and filling in the user you would like this to run under.  
`nano /etc/systemd/system/jobs-lndg.service`
```
[Unit]
Description=Run Jobs For Lndg
[Service]
User=<run_as_user>
Group=<run_as_user>
ExecStart=/usr/bin/bash /home/<run_as_user>/lndg/jobs.sh
StandardError=append:/var/log/lnd_jobs_error.log
```

Create a timer file for `jobs.py`, copying the contents below to the file and change the 20s refresh if you like..  
`nano /etc/systemd/system/jobs-lndg.timer`
```
[Unit]
Description=Run Lndg Jobs Every 20 Seconds
[Timer]
OnBootSec=300
OnUnitActiveSec=20
AccuracySec=1
[Install]
WantedBy=timers.target
```
Enable the timer to run the jobs service file at the specified interval.  
`sudo systemctl enable jobs-lndg.timer`  
`sudo systemctl start jobs-lndg.timer`  

## Rebalancer Runs
Create a simple bash file to call `rebalancer.py`, copying the contents below to the file.  
`nano /home/<run_as_user>/lndg/rebalancer.sh`
```
#!/bin/bash

/home/<run_as_user>/lndg/.venv/bin/python /home/<run_as_user>/lndg/rebalancer.py
```
Create a service file for `rebalancer.py`, copying the contents below to the file and filling in the user you would like this to run under.  
`nano /etc/systemd/system/rebalancer-lndg.service`
```
[Unit]
Description=Run Rebalancer For Lndg
[Service]
User=<run_as_user>
Group=<run_as_user>
ExecStart=/usr/bin/bash /home/<run_as_user>/lndg/rebalancer.sh
StandardError=append:/var/log/lnd_rebalancer_error.log
RuntimeMaxSec=3600
```

Create a timer file for `rebalancer.py`, copying the contents below to the file and change the 20s refresh if you like.  
`nano /etc/systemd/system/rebalancer-lndg.timer`
```
[Unit]
Description=Run Lndg Rebalancer Every 20 Seconds
[Timer]
OnBootSec=315
OnUnitActiveSec=20
AccuracySec=1
[Install]
WantedBy=timers.target
```
Enable and start the timer to run the rebalancer service file at the specified interval.  
`sudo systemctl enable rebalancer-lndg.timer`  
`sudo systemctl start rebalancer-lndg.timer`  


## Status Checks
You can check on the status of your timers.  
`sudo systemctl status jobs-lndg.timer`  
`sudo systemctl status rebalancer-lndg.timer`  

You can also check to make sure the last run of the service files triggered by the timers were successful.  
`sudo systemctl status jobs-lndg.service`  
`sudo systemctl status rebalancer-lndg.service`  

You can disable your timers as well if you would like them to stop.  
`sudo systemctl disable jobs-lndg.timer`  
`sudo systemctl stop jobs-lndg.timer`  
`sudo systemctl disable rebalancer-lndg.timer`  
`sudo systemctl stop rebalancer-lndg.timer`  
