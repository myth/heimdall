#!/bin/bash

set -euxo pipefail

docker build -t ghcr.io/myth/heimdall:latest .
docker push ghcr.io/myth/heimdall:latest
ssh aegis 'cd /srv/www/heimdall && docker compose pull && docker compose up -d'
