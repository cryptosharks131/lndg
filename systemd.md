# Systemd Setup For Backend Tools

- **You will need to fill in the proper username below in the paths marked `<run_as_user>`.**
- **This assumes you have installed lndg on the home directory of the user. For example, user `mynode` will have a home directory of `/home/mynode/`.**

## Backend Controller Setup
Create a service file for `controller.py`, copying the contents below to the file and filling in the user you would like this to run under.  
`nano /etc/systemd/system/lndg-controller.service`
```
[Unit]
Description=Backend Controller For Lndg
[Service]
Environment=PYTHONUNBUFFERED=1
User=<run_as_user>
Group=<run_as_user>
ExecStart=/home/<run_as_user>/lndg/.venv/bin/python /home/<run_as_user>/lndg/controller.py
StandardOutput=append:/var/log/lndg-controller.log
StandardError=append:/var/log/lndg-controller.log
Restart=always
RestartSec=60s
[Install]
WantedBy=multi-user.target
```
Enable and start the service to run the backend controller.  
`sudo systemctl enable lndg-controller.service`  
`sudo systemctl start lndg-controller.service`

## Additional Commands
You can also check on the status, disable or stop the backend controller.  
`sudo systemctl status lndg-controller.service`  
`sudo systemctl disable lndg-controller.service`  
`sudo systemctl stop lndg-controller.service`  
