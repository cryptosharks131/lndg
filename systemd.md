# Systemd Setup For Backend Tools

- **You will need to fill in the proper username below in the paths marked `<run_as_user>`.**
- **This assumes you have installed lndg on the home directory of the user. For example, user `mynode` will have a home directory of `/home/mynode/`.**

## Backend Controller Setup
Create a service file for `controller.py`, copying the contents below to the file and filling in the user you would like this to run under.  
`nano /etc/systemd/system/controller-lndg.service`
```
[Unit]
Description=Backend Controller For Lndg
[Service]
Environment=PYTHONUNBUFFERED=1
User=<run_as_user>
Group=<run_as_user>
ExecStart=/home/<run_as_user>/lndg/.venv/bin/python /home/<run_as_user>/lndg/controller.py
StandardOuput=append:/var/log/controller-lndg.log
StandardError=append:/var/log/controller-lndg-error.log
Restart=always
RestartSec=60s
[Install]
WantedBy=multi-user.target
```
Enable and start the service to run the backend controller.  
`sudo systemctl enable controller-lndg.service`  
`sudo systemctl start controller-lndg.service`

## Additional Commands
You can also check on the status, disable or stop the backend controller.  
`sudo systemctl status controller-lndg.service`  
`sudo systemctl disable controller-lndg.service`  
`sudo systemctl stop controller-lndg.service`  
