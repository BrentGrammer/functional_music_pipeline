#!/bin/bash

#######
# Quick Starts Gemini CLI in API key mode using template
######

chmod +x ./scripts/start_docker.sh
./scripts/start_docker.sh

code .

sbx policy allow network generativelanguage.googleapis.com
sbx policy allow network gemini-api-docs-mcp.dev
sbx policy allow network ai.google.dev
sbx policy allow network oauth2.googleapis.com
sbx policy allow network accounts.google.com
sbx policy allow network play.googleapis.com

sbx run gemini .
