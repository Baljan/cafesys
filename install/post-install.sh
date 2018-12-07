#!/bin/bash

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
COMPONENTS_ROOT="${SCRIPT_DIR}/components"

declare -a COMPONENTS=(
    "cafesys"
    "docker"
    "docker-compose"
    "cloud-sql-proxy"
    "deploy-script"
)

for i in "${COMPONENTS[@]}"
do
    # Install each component with root level access
    sudo -E "${COMPONENTS_ROOT}/$i.sh"
done
