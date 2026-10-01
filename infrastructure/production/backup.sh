#!/bin/sh
set -eu

environment_file=${1:-.env.production}
backup_directory=${2:-./backups}
compose_file=${COMPOSE_FILE:-compose.production.yaml}
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
backup_file="$backup_directory/crm-$timestamp.dump"
temporary_file="$backup_file.tmp"

umask 077
mkdir -p "$backup_directory"

cleanup() {
  rm -f "$temporary_file"
}
trap cleanup EXIT INT TERM

docker compose --env-file "$environment_file" -f "$compose_file" exec -T database \
  sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" exec pg_dump --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --format=custom --no-owner --no-privileges' \
  > "$temporary_file"

docker compose --env-file "$environment_file" -f "$compose_file" exec -T database \
  pg_restore --list < "$temporary_file" > /dev/null

mv "$temporary_file" "$backup_file"
sha256sum "$backup_file" > "$backup_file.sha256"
trap - EXIT INT TERM
printf '%s\n' "$backup_file"
