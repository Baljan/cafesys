#!/bin/bash

# Configuration variables
export APP_USER=cafesys
export APP_GROUP=cafesys
export ORGANIZATION_DIR=/opt/baljan
export INSTALLATION_DIR=${ORGANIZATION_DIR}/cafesys
export RUNTIME_DIR=${ORGANIZATION_DIR}/run
export DEPLOY_SCRIPT=${ORGANIZATION_DIR}/deploy-cafesys.sh

# Install minimal set of dependencies
sudo apt-get -y install git

# Create organisation directory
sudo mkdir -p ${ORGANIZATION_DIR}

# Temporarily make the current user the owner of the organization directory
# so that we can install the application properly
sudo chown -R ${USER}:$USER ${ORGANIZATION_DIR}

# Clone git repository into installation directory
if [[ ! -d "${INSTALLATION_DIR}" ]]; then
    sudo git clone https://github.com/Baljan/cafesys.git ${INSTALLATION_DIR}
    sudo git -C ${INSTALLATION_DIR} checkout gcp
else
    # If the currently installed application does not contain a git repository we exit the installation
    if [[ ! -d "${INSTALLATION_DIR}/.git" ]]; then
        echo "The installation directory ${INSTALLATION_DIR} already exists but does not contain a git repository."
        echo
        echo "The installation script has been aborted to avoid unwanted loss of data."
        echo "Please follow the below steps in order to continue installation"
        echo "  1. Make a backup of ${INSTALLATION_DIR}"
        echo "  2. Remove ${INSTALLATION_DIR} and all of its content"
        echo "  3. Re-run the installation script"

        exit 1
    else
        sudo git -C ${INSTALLATION_DIR} pull
    fi
fi

# Install dependencies and configure environment
bash "${INSTALLATION_DIR}/install/post-install.sh"

# Hand over control to the deployment procedure
sudo su ${APP_USER} -c "${DEPLOY_SCRIPT}"
