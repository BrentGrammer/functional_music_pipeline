#!/bin/bash

DIR_NAME="$(basename "$PWD")"
CLEAN_NAME="${DIR_NAME//_/-}"
SANDBOX_NAME="codex-$CLEAN_NAME"

chmod +x ./scripts/start_docker.sh
./scripts/start_docker.sh

code .

# requires logging in and setting secret (copy url this shows and login with Plus Subscription account):
#  sbx secret set -g openai --oauth

sbx policy allow network -g chatgpt.com:443

if sbx ls | grep "$SANDBOX_NAME"; then
    # Copy project npm config into the Docker sandbox user's npm config location
    if [ -f .npmrc ]; then
    sbx cp .npmrc "$SANDBOX_NAME":/home/agent/.npmrc
    fi
else
    echo "!!! WARNING !!! No sandbox $SANDBOX_NAME found!"
    echo "    After creating/running the sandbox, run 'sbx cp .npmrc ""$SANDBOX_NAME"":/home/agent/.npmrc' to get .npmrc config moved into it"
fi


sbx run codex -- --sandbox workspace-write --cd . -c analytics.enabled=false
