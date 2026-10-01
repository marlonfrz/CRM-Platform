#!/bin/sh
set -eu

environment_file=${1:?Usage: restore-check.sh ENV_FILE BACKUP_FILE}
backup_file=${2:?Usage: restore-check.sh ENV_FILE BACKUP_FILE}
compose_file=${COMPOSE_FILE:-compose.production.yaml}
restore_database="crm_restore_check_$(date -u +%Y%m%d%H%M%S)"

test -f "$backup_file"
test -f "$backup_file.sha256"
sha256sum -c "$backup_file.sha256"

cleanup() {
  docker compose --env-file "$environment_file" -f "$compose_file" exec -T database \
    sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" dropdb --if-exists --force --username="$POSTGRES_USER" "$1"' -- "$restore_database" > /dev/null
}
trap cleanup EXIT INT TERM

docker compose --env-file "$environment_file" -f "$compose_file" exec -T database \
  sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" createdb --username="$POSTGRES_USER" "$1"' -- "$restore_database"

docker compose --env-file "$environment_file" -f "$compose_file" exec -T database \
  sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" pg_restore --exit-on-error --no-owner --no-privileges --username="$POSTGRES_USER" --dbname="$1"' -- "$restore_database" \
  < "$backup_file"

docker compose --env-file "$environment_file" -f "$compose_file" exec -T database \
  sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" psql --username="$POSTGRES_USER" --dbname="$1" --tuples-only --command="SELECT version_num FROM alembic_version"' -- "$restore_database"
