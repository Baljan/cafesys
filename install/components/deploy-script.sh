#!/bin/bash
: ${INSTALLATION_DIR:?"Need to set INSTALLATION_DIR non-empty"}
: ${RUNTIME_DIR:?"Need to set RUNTIME_DIR non-empty"}

DEPLOY_SCRIPT="${INSTALLATION_DIR}/deploy-cafesys.sh"

cat >${DEPLOY_SCRIPT} <<EOL
#!/bin/bash
cd ${INSTALLATION_DIR}
git pull
bash ${INSTALLATION_DIR}/install/deploy.sh ${INSTALLATION_DIR} ${RUNTIME_DIR}
EOL

chmod +x ${DEPLOY_SCRIPT}
