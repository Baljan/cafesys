#!/bin/bash

# Install Docker
apt-get update
apt-get -y install apt-transport-https ca-certificates curl gnupg2 software-properties-common
curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add -
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/debian $(lsb_release -cs) stable"
apt-get update
apt-get -y install docker-ce

# Authenticate with Container Registry (configures Docker to pull from our registry)
gcloud auth configure-docker
