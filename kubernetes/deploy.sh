#!/bin/bash

confirm() {
    read -p "$1 [Y/n]" -n 1 -r
    [[ ! -z $REPLY ]] && echo
    if [[ $REPLY =~ ^(Y|y)$ ]] || [[ -z $REPLY ]]; then
        return 0
    else
        return 1
    fi
}

approve() {
    read -p "$1 [y/N]" -n 1 -r
    [[ ! -z $REPLY ]] && echo
    if [[ $REPLY =~ ^(Y|y)$ ]]; then
        return 0
    else
        return 1
    fi
}

prompt() {
    read -p "$2 [$3]: " $1
    [ -z "${!1}" ] && export $1=$3
}

echo "Would you like to configure kubectl for Google Cloud?"
confirm " NOTE: This is a global configuration on your machine!"
if [[ $? -eq "0" ]]; then
    prompt PROJECT_NAME "  What project is your cluster in?" sektionscafe-baljan
    prompt ZONE_NAME    "  What zone is your cluster in?" europe-west1-b
    prompt CLUSTER_NAME "  What cluster do you want to deploy to?" cluster
    gcloud container clusters get-credentials "$CLUSTER_NAME" --zone "$ZONE_NAME" --project "$PROJECT_NAME"
fi

echo
echo "Configured kubectl context:"
echo "  `kubectl config current-context`"
echo
confirm "Would you like to continue deploying using this context?"
if [[ $? -eq "1" ]]; then
    exit 1
fi

echo "  Setting up base cluster components..."
kubectl create namespace baljan -o yaml --dry-run | kubectl apply -f -
echo "  Done!"

echo
echo "Would you like to dump the environment variables set in the cluster?"
approve " NOTE: This will OVERWRITE the contents of .env!"
if [[ $? -eq "0" ]]; then
    kubectl get configmap baljan-config --namespace=baljan -o go-template-file --template=env-export.go > .env
    echo "  Configuration dumped to .env"
fi

echo
approve "Would you like to update the cluster configuration with your .env?"
if [[ $? -eq "0" ]]; then
    echo
    echo "Validating environment variables..."
    ./test-env.sh
    if [[ $? -eq "1" ]]; then
        exit 1
    fi

    kubectl create configmap baljan-config --from-env-file=.env -n baljan -o yaml --dry-run | kubectl apply -f -
fi

echo
echo "IMPORTANT INFORMATION ABOUT THE DEPLOYMENT"
echo "------------------------------------------"
echo
echo "The traefik deployment might fail if you are not configured as a"
echo " cluster administrator. This can be solved by running the following"
echo " command, properly replacing the name and e-mail address:"
echo
echo "  kubectl create clusterrolebinding <name here> --clusterrole=cluster-admin --user=<your.google.cloud.email@example.org>"
echo
echo
echo "The kubernetes yaml files are configured to use an already configured"
echo " database in the Google cloud. This is setup using the gce-proxy image"
echo " in kube.yaml."
echo "If you are not deploying against this exact cluster and database you"
echo " will need to follow the following guide and modify kube.yaml"
echo " accordingly:"
echo
echo "  https://cloud.google.com/sql/docs/mysql/connect-kubernetes-engine"
echo
echo
echo "As a last warning before deploying you might not be able to access the"
echo " needed docker images for the blipp or cafesys if you are running outside"
echo " of the production cluster."
echo
approve "Are you sure that you want to continue?"
if [[ $? -eq "1" ]]; then
    exit 1
fi

echo "Deploying..."
kubectl apply -f kube.yaml
kubectl apply -f traefik.yaml
echo "Done!"

