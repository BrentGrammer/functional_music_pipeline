#!/bin/bash

#######
# Quick Starts Gemini CLI in API key mode using template
######

chmod +x ./scripts/start_docker.sh
./scripts/start_docker.sh

code .

sbx policy allow network -g generativelanguage.googleapis.com
sbx policy allow network -g gemini-api-docs-mcp.dev
sbx policy allow network -g ai.google.dev
sbx policy allow network -g oauth2.googleapis.com
sbx policy allow network -g accounts.google.com
sbx policy allow network -g play.googleapis.com

sbx run gemini .
