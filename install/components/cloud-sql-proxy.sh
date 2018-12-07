#!/bin/bash

# Install Cloud SQL Proxy
wget https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 -O /usr/local/bin/cloud_sql_proxy
chmod +x /usr/local/bin/cloud_sql_proxy

# Create Cloud SQL Proxy service
cat >/etc/systemd/system/cloud_sql_proxy.service <<EOL
[Install]
WantedBy=multi-user.target

[Unit]
Description=Google Cloud Compute Engine SQL Proxy
Requires=networking.service
After=networking.service

[Service]
Type=simple
WorkingDirectory=/usr/local/bin/
ExecStart=/usr/local/bin/cloud_sql_proxy -instances=sektionscafe-baljan:europe-west1:baljan-db=tcp:3306
Restart=always
StandardOutput=journal
User=root
EOL

# Reload services
systemctl daemon-reload
systemctl enable cloud_sql_proxy
systemctl start cloud_sql_proxy
