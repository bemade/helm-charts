#!/bin/bash
set -e

# Environment variables passed to the container
echo "Connecting to PostgreSQL at $HOST:$PORT as $ADMIN_USER"
PGPASSWORD="$ADMIN_PASSWORD"; psql -v ON_ERROR_STOP=1 --host="$HOST" --port="$PORT" --username="$ADMIN_USER" --dbname="postgres" <<-EOSQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = '$NEW_USER') THEN
    CREATE USER "$NEW_USER" WITH PASSWORD '$NEW_PASSWORD' CREATEDB;
  END IF;
END
\$\$;
EOSQL
