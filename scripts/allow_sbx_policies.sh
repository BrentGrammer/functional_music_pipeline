#!/usr/bin/env bash

# Policies to allow in docker sandbox when in locked down mode

set -euo pipefail

# Allow docker for pulling templates with sbx
sbx policy allow network -g -g download.docker.com:443

# Allow ubuntu security updates for patches and package upgrades
sbx policy allow network -g -g debian.org:443
sbx policy allow network -g -g ports.ubuntu.com:80
sbx policy allow network -g -g ports.ubuntu.com:443
sbx policy allow network -g -g deb.debian.org:443
sbx policy allow network -g -g archive.ubuntu.com:443
sbx policy allow network -g -g security.ubuntu.com:443

# Allow dependency registries
sbx policy allow network -g -g registry.npmjs.org:443
sbx policy allow network -g -g pypi.org:443
sbx policy allow network -g -g files.pythonhosted.org:443

# Allow AWS Bedrock
sbx policy allow network -g bedrock-runtime.us-west-2.amazonaws.com:443
sbx policy allow network -g bedrock-runtime.us-east-1.amazonaws.com:443

# Allow Google gemini
sbx policy allow network -g generativelanguage.googleapis.com:443
sbx policy allow network -g gemini-api-docs-mcp.dev:443
sbx policy allow network -g ai.google.dev:443
sbx policy allow network -g oauth2.googleapis.com:443
sbx policy allow network -g accounts.google.com:443
sbx policy allow network -g cloudcode-pa.googleapis.com:443
sbx policy allow network -g play.googleapis.com:443
sbx policy allow network -g www.googleapis.com:443

# Allow OpenAI for codex Pro subscription
sbx policy allow network -g chatgpt.com:443
sbx policy allow network -g api.openai.com:443

# For Exa mcp
sbx policy allow network -g mcp.exa.ai:443

# Needed for Serena mcp
sbx policy allow network -g github.com:443
sbx policy allow network -g api.github.com:443
sbx policy allow network -g oraios-software.de:443