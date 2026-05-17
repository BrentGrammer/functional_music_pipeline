#!/bin/bash

chmod +x ./scripts/start_docker.sh
./scripts/start_docker.sh

code .

# requires logging in and setting secret (copy url this shows and login with Plus Subscription account):
#  sbx secret set -g openai --oauth

sbx policy allow network chatgpt.com:443

sbx run codex -- --sandbox workspace-write --cd . -c analytics.enabled=false
