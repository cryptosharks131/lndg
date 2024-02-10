#!/bin/bash

INSTALL_USER=${SUDO_USER:-${USER}}
NODE_IP=$(hostname -I | cut -d' ' -f1)

if [ "$INSTALL_USER" == 'root' ]; then
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

# Ensure the lndg directory exists
mkdir -p $LNDG_DIR
mkdir -p $LNDG_DIR/.venv/bin
mkdir -p /var/log/uwsgi

function install_deps() {
    apt-get update
    apt-get install -y python3-dev build-essential python3-pip uwsgi nginx
    python3 -m pip install uwsgi
}

function setup_uwsgi() {
    # Creating the lndg.ini file
    cat << EOF > $LNDG_DIR/lndg.ini
# lndg.ini file
[uwsgi]
# Django-related settings
chdir           = $LNDG_DIR
module          = lndg.wsgi
home            = $LNDG_DIR/.venv
logto           = /var/log/uwsgi/%n.log

# process-related settings
master          = true
processes       = 1
socket          = $LNDG_DIR/lndg.sock
chmod-socket    = 660
vacuum          = true
EOF

    # Creating the uwsgi_params file
    cat << EOF > $LNDG_DIR/uwsgi_params
uwsgi_param  QUERY_STRING       \$query_string;
uwsgi_param  REQUEST_METHOD     \$request_method;
uwsgi_param  CONTENT_TYPE       \$content_type;
uwsgi_param  CONTENT_LENGTH     \$content_length;

uwsgi_param  REQUEST_URI        "\$request_uri";
uwsgi_param  PATH_INFO          "\$document_uri";
uwsgi_param  DOCUMENT_ROOT      "\$document_root";
uwsgi_param  SERVER_PROTOCOL    "\$server_protocol";
uwsgi_param  REQUEST_SCHEME     "\$scheme";
uwsgi_param  HTTPS              "\$https if_not_empty";

uwsgi_param  REMOTE_ADDR        "\$remote_addr";
uwsgi_param  REMOTE_PORT        "\$remote_port";
uwsgi_param  SERVER_PORT        "\$server_port";
uwsgi_param  SERVER_NAME        "\$server_name";
EOF

    # Creating the uwsgi.service systemd unit file
    cat << EOF > /etc/systemd/system/uwsgi.service
[Unit]
Description=Lndg uWSGI app
After=syslog.target

[Service]
ExecStart=$LNDG_DIR/.venv/bin/uwsgi --ini $LNDG_DIR/lndg.ini
User=$INSTALL_USER
Group=www-data
Restart=on-failure
KillSignal=SIGQUIT
Type=notify
StandardError=syslog
NotifyAccess=all

[Install]
WantedBy=multi-user.target
EOF
    usermod -a -G www-data $INSTALL_USER
}

function setup_nginx() {
    # Creating the Nginx configuration file
    cat << EOF > /etc/nginx/sites-available/lndg
upstream django {
    server unix://$LNDG_DIR/lndg.sock; # for a file socket
}

server {
    listen      8889;
    server_name _;
    charset     utf-8;
    client_max_body_size 75M;
    proxy_read_timeout 180;

    location /static {
        alias $LNDG_DIR/gui/static; # your Django project's static files - amend as required
    }

    location / {
        uwsgi_pass  django;
        include     $LNDG_DIR/uwsgi_params; # the uwsgi_params file
    }
}
EOF

    # Remove the default site and link the new site
    rm /etc/nginx/sites-enabled/default
    ln -sf /etc/nginx/sites-available/lndg /etc/nginx/sites-enabled/
}

function start_services() {
    touch /var/log/uwsgi/lndg.log
    touch $LNDG_DIR/lndg.sock
    chgrp www-data /var/log/uwsgi/lndg.log
    chgrp www-data $LNDG_DIR/lndg.sock
    chmod 660 /var/log/uwsgi/lndg.log
    systemctl start uwsgi
    systemctl restart nginx
    systemctl enable uwsgi
    systemctl enable nginx
}

function report_information() {
    echo "Nginx and uWSGI have been set up with user $INSTALL_USER at $NODE_IP:8889."
}

##### Main #####
echo -e "Setting up, this may take a few minutes..."
check_path
install_deps
setup_uwsgi
setup_nginx
start_services
report_information