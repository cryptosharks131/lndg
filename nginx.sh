INSTALL_USER=${SUDO_USER:-${USER}}
NODE_IP=$(hostname -I | cut -d' ' -f1)
RED='\033[0;31m'
NC='\033[0m'

function install_deps() {
    apt install -y python3-dev >/dev/null 2>&1
    apt install -y build-essential python >/dev/null 2>&1
    apt install -y uwsgi >/dev/null 2>&1
    apt install -y nginx >/dev/null 2>&1
    /home/$INSTALL_USER/lndg/.venv/bin/python -m pip install uwsgi >/dev/null 2>&1
}

function steup_uwsgi() {
    cat << EOF > /home/$INSTALL_USER/lndg/lndg.ini
# lndg.ini file
[uwsgi]

# Django-related settings
# the base directory (full path)
chdir           = /home/$INSTALL_USER/lndg
# Django's wsgi file
module          = lndg.wsgi
# the virtualenv (full path)
home            = /home/$INSTALL_USER/lndg/.venv
#location of log files
logto           = /var/log/uwsgi/%n.log

# process-related settings
# master
master          = true
# maximum number of worker processes
processes       = 1
# the socket (use the full path to be safe
socket          = /home/$INSTALL_USER/lndg/lndg.sock
# ... with appropriate permissions - may be needed
chmod-socket    = 660
# clear environment on exit
vacuum          = true
EOF
    cat <<\EOF > /home/$INSTALL_USER/lndg/uwsgi_params

uwsgi_param  QUERY_STRING       $query_string;
uwsgi_param  REQUEST_METHOD     $request_method;
uwsgi_param  CONTENT_TYPE       $content_type;
uwsgi_param  CONTENT_LENGTH     $content_length;

uwsgi_param  REQUEST_URI        "$request_uri";
uwsgi_param  PATH_INFO          "$document_uri";
uwsgi_param  DOCUMENT_ROOT      "$document_root";
uwsgi_param  SERVER_PROTOCOL    "$server_protocol";
uwsgi_param  REQUEST_SCHEME     "$scheme";
uwsgi_param  HTTPS              "$https if_not_empty";

uwsgi_param  REMOTE_ADDR        "$remote_addr";
uwsgi_param  REMOTE_PORT        "$remote_port";
uwsgi_param  SERVER_PORT        "$server_port";
uwsgi_param  SERVER_NAME        "$server_name";
EOF
    cat << EOF > /etc/systemd/system/uwsgi.service
[Unit]
Description=Lndg uWSGI app
After=syslog.target

[Service]
ExecStart=/home/$INSTALL_USER/lndg/.venv/bin/uwsgi \
--ini /home/$INSTALL_USER/lndg/lndg.ini
User=$INSTALL_USER
Group=www-data
Restart=on-failure
KillSignal=SIGQUIT
Type=notify
StandardError=syslog
NotifyAccess=all

[Install]
WantedBy=sockets.target
EOF
    usermod -a -G www-data $INSTALL_USER
}

function steup_nginx() {
    cat << EOF > /etc/nginx/sites-enabled/lndg
upstream django {
    server unix:///home/$INSTALL_USER/lndg/lndg.sock; # for a file socket
}

server {
    # the port your site will be served on, use port 80 unless setting up ssl certs, then 443
    listen      $NODE_IP:80;
    # optional settings for ssl setup
    #ssl on;
    #ssl_certificate /<path_to_certs>/fullchain.pem;
    #ssl_certificate_key /<path_to_certs>/privkey.pem;
    # the domain name it will serve for
    server_name $NODE_IP; # you can substitute your node IP address or a custom domain like lndg.local (just make sure to update your local hosts file)
    charset     utf-8;

    # max upload size
    client_max_body_size 75M;   # adjust to taste

    # max wait for django time
    proxy_read_timeout 180;

    # Django media
    location /static {
        alias /home/$INSTALL_USER/lndg/gui/static; # your Django project's static files - amend as required
    }

    # Finally, send all non-media requests to the Django server.
    location / {
        uwsgi_pass  django;
        include     /home/$INSTALL_USER/lndg/uwsgi_params; # the uwsgi_params file
    }
}
EOF
    rm /etc/nginx/sites-enabled/default
}

function start_services() {
    touch /var/log/uwsgi/lndg.log
    touch /home/$INSTALL_USER/lndg/lndg.sock
    chgrp www-data /var/log/uwsgi/lndg.log
    chgrp www-data /home/$INSTALL_USER/lndg/lndg.sock
    chmod 660 /var/log/uwsgi/lndg.log
    systemctl start uwsgi
    systemctl restart nginx
    sudo systemctl enable uwsgi
    sudo systemctl enable nginx
}

function report_information() {
    echo -e ""
    echo -e "================================================================================================================================"
    echo -e "Nginx service setup using user account $INSTALL_USER and a IP address of $NODE_IP."
    echo -e ""
    echo -e "uWSGI Status: ${RED}sudo systemctl status uwsgi.service${NC}"
    echo -e "Nginx Status: ${RED}sudo systemctl status nginx.service${NC}"
    echo -e ""
    echo -e "To disable your webserver, use the following commands."
    echo -e "Disable uWSGI: ${RED}sudo systemctl disable uwsgi.service${NC}"
    echo -e "Disable Nginx: ${RED}sudo systemctl disable nginx.service${NC}"
    echo -e "Stop uWSGI: ${RED}sudo systemctl stop uwsgi.service${NC}"
    echo -e "Stop Nginx: ${RED}sudo systemctl stop nginx.service${NC}"
    echo -e ""
    echo -e "To re-enable these services, simply replace the disable/stop commands with enable/start."
    echo -e "================================================================================================================================"
}

##### Main #####
echo -e "Setting up, this may take a few minutes..."
install_deps
steup_uwsgi
steup_nginx
start_services
report_information