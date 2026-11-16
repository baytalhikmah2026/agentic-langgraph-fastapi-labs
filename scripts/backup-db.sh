#!/usr/bin/env bash
# Lab 33: back up the project's PostgreSQL database (clients, users, checkpoints) to backups/.
# Run it from the project folder with the stack started:  bash scripts/backup-db.sh
set -euo pipefail

stamp=$(date +%Y%m%d-%H%M%S)
target="backups/sovereign_brain-$stamp.dump"
mkdir -p backups
docker compose exec -T postgres pg_dump -U sb -d sovereign_brain -Fc -f /tmp/backup.dump
docker compose cp postgres:/tmp/backup.dump "$target"
docker compose exec -T postgres rm /tmp/backup.dump
echo "Backup written to $target"
