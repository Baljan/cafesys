#!/bin/bash

# Exit on any error
set -e

# Configuration variables
PROJECT=sektionscafe-baljan
VM_NAME=cafesys
SERVICE_ACCOUNT=cafesys-service-account

# Variable expansion
SERVICE_ACCOUNT_DOMAIN=${PROJECT}.iam.gserviceaccount.com
FULL_SERVICE_ACCOUNT_NAME=${SERVICE_ACCOUNT}@${SERVICE_ACCOUNT_DOMAIN}

# Create a service account for the VM instance
gcloud iam service-accounts create ${SERVICE_ACCOUNT} --display-name="Service account for the cafesys VM"

# Give the service account permission to connect to the SQL server
gcloud projects add-iam-policy-binding ${PROJECT} \
  --member serviceAccount:${FULL_SERVICE_ACCOUNT_NAME} \
  --role roles/cloudsql.client

# Give the service account permission to fetch our docker images
gcloud projects add-iam-policy-binding ${PROJECT} \
  --member serviceAccount:${FULL_SERVICE_ACCOUNT_NAME} \
  --role roles/storage.objectViewer

# Create the instance
gcloud compute instances create ${VM_NAME} \
--zone europe-west2-c \
--machine-type g1-small \
--image-family debian-9 \
--image-project debian-cloud \
--boot-disk-size 10GB \
--boot-disk-type pd-standard \
--service-account ${FULL_SERVICE_ACCOUNT_NAME}
