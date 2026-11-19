#!/usr/bin/env bash
# Runs once, when the Postgres data volume is empty (official image behaviour).
# Creates one database + one login role per service and blocks every other role from
# connecting, so a service physically cannot query another service's data.
# To re-run after changing it: `docker compose down -v` (DELETES all local data).
set -euo pipefail

: "${USER_SVC_DB_PASSWORD:?USER_SVC_DB_PASSWORD must be set}"
: "${CATALOG_SVC_DB_PASSWORD:?CATALOG_SVC_DB_PASSWORD must be set}"
: "${RECO_SVC_DB_PASSWORD:?RECO_SVC_DB_PASSWORD must be set}"

create_service_database() {
  local db="$1" role="$2" password="$3"
  # psql variables (:"x" = quoted identifier, :'x' = quoted literal) avoid SQL injection
  # through the env values and keep the password out of the process list.
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
    -v db="$db" -v role="$role" -v password="$password" <<'SQL'
CREATE ROLE :"role" LOGIN PASSWORD :'password';
CREATE DATABASE :"db" OWNER :"role";
-- By default PUBLIC (every role) may CONNECT to every database. Remove that.
REVOKE ALL ON DATABASE :"db" FROM PUBLIC;
SQL
  echo "created database ${db} owned by ${role}"
}

create_service_database user_db    user_svc    "$USER_SVC_DB_PASSWORD"
create_service_database catalog_db catalog_svc "$CATALOG_SVC_DB_PASSWORD"
create_service_database reco_db    reco_svc    "$RECO_SVC_DB_PASSWORD"

# Service roles have no reason to connect to the maintenance database either.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
  -c 'REVOKE CONNECT ON DATABASE postgres FROM PUBLIC;'
