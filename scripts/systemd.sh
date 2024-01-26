INSTALL_USER=${SUDO_USER:-${USER}}
REFRESH=20
RED='\033[0;31m'
NC='\033[0m'

if [ "$INSTALL_USER" == 'root' ] >/dev/null 2>&1; then
    HOME_DIR='/root'
else
    HOME_DIR="/home/$INSTALL_USER"
fi
LNDG_DIR="$HOME_DIR/lndg"

function check_path() {
    if [ -e $LNDG_DIR/lndg/wsgi.py ]; then
        echo "Using LNDg installation found at $LNDG_DIR"
    else
        echo "LNDg installation not found at $LNDG_DIR/, please provide the correct path:"
        read USR_DIR
        if [ -e $USR_DIR/lndg/wsgi.py ]; then
            LNDG_DIR=$USR_DIR
            echo "Using LNDg installation found at $LNDG_DIR"
        else
            echo "LNDg installation still not found, exiting..."
            exit 1
        fi
    fi
}

function configure_controller() {
    cat << EOF > /etc/systemd/system/lndg-controller.service
[Unit]
Description=Run Backend Controller For Lndg
[Service]
Environment=PYTHONUNBUFFERED=1
User=$INSTALL_USER
Group=$INSTALL_USER
ExecStart=$LNDG_DIR/.venv/bin/python $LNDG_DIR/controller.py
StandardOutput=append:/var/log/lndg-controller.log
StandardError=append:/var/log/lndg-controller.log
Restart=always
RestartSec=60s
[Install]
WantedBy=multi-user.target
EOF
}

function enable_services() {
    systemctl daemon-reload
    sleep 3
    systemctl start lndg-controller.service
    systemctl enable lndg-controller.service >/dev/null 2>&1
}

function report_information() {
    echo -e ""
    echo -e "================================================================================================================================"
    echo -e "Backend services and rebalancer setup for LNDg via systemd using user account $INSTALL_USER and a refresh interval of $REFRESH seconds."
    echo -e ""
    echo -e "Backend Controller Status: ${RED}sudo systemctl status lndg-controller.service${NC}"
    echo -e ""
    echo -e "To disable your backend services, use the following commands."
    echo -e "Disable Backend Controller: ${RED}sudo systemctl disable lndg-controller.service${NC}"
    echo -e "Stop Backend Controller: ${RED}sudo systemctl stop lndg-controller.service${NC}"
    echo -e ""
    echo -e "To re-enable these services, simply replace the disable/stop commands with enable/start."
    echo -e "================================================================================================================================"
}

##### Main #####
echo -e "Setting up, this may take a few minutes..."
check_path
configure_controller
enable_services
report_information