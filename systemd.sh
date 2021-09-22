INSTALL_USER=${SUDO_USER:-${USER}}
REFRESH=20
RED='\033[0;31m'
NC='\033[0m'

function configure_jobs() {
    cat << EOF > /home/$INSTALL_USER/lndg/gui/jobs.sh
#!/bin/bash

/home/$INSTALL_USER/lndg/.venv/bin/python /home/$INSTALL_USER/lndg/gui/jobs.py
EOF

    cat << EOF > /etc/systemd/system/jobs-lndg.service
[Unit]
Description=Run Jobs For Lndg
[Service]
User=$INSTALL_USER
Group=$INSTALL_USER
ExecStart=/usr/bin/bash /home/$INSTALL_USER/lndg/gui/jobs.sh
StandardError=append:/var/log/lnd_jobs_error.log
EOF

    cat << EOF > /etc/systemd/system/jobs-lndg.timer
[Unit]
Description=Run Lndg Jobs Every $REFRESH Seconds
[Timer]
OnBootSec=300
OnUnitActiveSec=$REFRESH
AccuracySec=1
[Install]
WantedBy=timers.target
EOF
}

function configure_rebalancer() {
    cat << EOF > /home/$INSTALL_USER/lndg/gui/rebalancer.sh
#!/bin/bash

/home/$INSTALL_USER/lndg/.venv/bin/python /home/$INSTALL_USER/lndg/gui/jobs.py
EOF

    cat << EOF > /etc/systemd/system/rebalancer-lndg.service
[Unit]
Description=Run Rebalancer For Lndg
[Service]
User=$INSTALL_USER
Group=$INSTALL_USER
ExecStart=/usr/bin/bash /home/$INSTALL_USER/lndg/gui/rebalancer.sh
StandardError=append:/var/log/lnd_rebalancer_error.log
RuntimeMaxSec=3600
EOF

    cat << EOF > /etc/systemd/system/rebalancer-lndg.timer
[Unit]
Description=Run Lndg Rebalancer Every $REFRESH Seconds
[Timer]
OnBootSec=315
OnUnitActiveSec=$REFRESH
AccuracySec=1
[Install]
WantedBy=timers.target
EOF
}

function enable_services() {
    systemctl daemon-reload
    sleep 3
    systemctl start jobs-lndg.timer
    systemctl enable jobs-lndg.timer >/dev/null 2>&1
    systemctl start rebalancer-lndg.timer
    systemctl enable rebalancer-lndg.timer >/dev/null 2>&1
}

function report_information() {
    echo -e ""
    echo -e "================================================================================================================================"
    echo -e "Backend services and rebalancer setup for LNDg via systemd using user account $INSTALL_USER and a refresh interval of $REFRESH seconds."
    echo -e ""
    echo -e "Jobs Timer Status: ${RED}sudo systemctl status jobs-lndg.timer${NC}"
    echo -e "Rebalancer Timer Status: ${RED}sudo systemctl status rebalancer-lndg.timer${NC}"
    echo -e ""
    echo -e "Last Jobs Status: ${RED}sudo systemctl status jobs-lndg.service${NC}"
    echo -e "Last Rebalancer Status: ${RED}sudo systemctl status rebalancer-lndg.service${NC}"
    echo -e ""
    echo -e "To disable your backend services, use the following commands."
    echo -e "Disable Jobs Timer: ${RED}sudo systemctl disable jobs-lndg.timer${NC}"
    echo -e "Disable Rebalancer Timer: ${RED}sudo systemctl disable rebalancer-lndg.timer${NC}"
    echo -e "Stop Jobs Timer: ${RED}sudo systemctl stop jobs-lndg.timer${NC}"
    echo -e "Stop Rebalancer Timer: ${RED}sudo systemctl stop rebalancer-lndg.timer${NC}"
    echo -e ""
    echo -e "To re-enable these services, simply replace the disable/stop commands with enable/start."
    echo -e "================================================================================================================================"
}

##### Main #####
echo -e "Setting up, this may take a few minutes..."
configure_jobs
configure_rebalancer
enable_services
report_information