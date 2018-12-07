#!/bin/bash
: ${APP_USER:?"Need to set APP_USER non-empty"}
: ${APP_GROUP:?"Need to set APP_GROUP non-empty"}
: ${ORGANIZATION_DIR:?"Need to set ORGANIZATION_DIR non-empty"}
: ${INSTALLATION_DIR:?"Need to set INSTALLATION_DIR non-empty"}
: ${RUNTIME_DIR:?"Need to set RUNTIME_DIR non-empty"}

# Create user if missing
id -u ${APP_USER} &>/dev/null || useradd ${APP_USER}

# Create group if missing
getent group ${APP_GROUP} || groupadd ${APP_GROUP}

# Add user to group
usermod -a -G ${APP_GROUP} ${APP_USER}

# Create a runtime directory
mkdir -p ${RUNTIME_DIR}

# Make sure that the organization and installation directories has correct permissions
chown -R ${APP_USER}:${APP_GROUP} ${ORGANIZATION_DIR}
chmod 770 ${ORGANIZATION_DIR}
chmod 770 ${INSTALLATION_DIR}
chmod 770 ${RUNTIME_DIR}
