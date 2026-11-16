# Lab 33: back up the project's PostgreSQL database (clients, users, checkpoints) to backups\.
# Run it from the project folder with the stack started:  .\scripts\backup-db.ps1
$ErrorActionPreference = "Stop"

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$target = "backups/sovereign_brain-$stamp.dump"
New-Item -ItemType Directory -Force -Path backups | Out-Null
docker compose exec -T postgres pg_dump -U sb -d sovereign_brain -Fc -f /tmp/backup.dump
if ($LASTEXITCODE -ne 0) { throw "pg_dump failed" }
docker compose cp postgres:/tmp/backup.dump $target
if ($LASTEXITCODE -ne 0) { throw "copy failed" }
docker compose exec -T postgres rm /tmp/backup.dump
Write-Output "Backup written to $target"
