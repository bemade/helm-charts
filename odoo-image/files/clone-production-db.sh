#!/bin/bash
set -e

# Environment variables
HOST=${PG_HOST}
PORT=${PG_PORT}
ADMIN_USER=${ADMIN_USER}
ADMIN_PASSWORD=${ADMIN_PASSWORD}
PROD_DB=${PROD_DB}
STAGING_DB=${STAGING_DB}
STAGING_USER=${STAGING_USER}

echo "Cloning production database ${PROD_DB} to staging database ${STAGING_DB}..."

# Check if staging database already exists
if psql -U "$ADMIN_USER" -h "$HOST" -p "$PORT" -lqt | cut -d \| -f 1 | grep -qw "$STAGING_DB"; then
  echo "Database $STAGING_DB already exists. Dropping database."
  psql -v ON_ERROR_STOP=1 -U "$ADMIN_USER" -h "$HOST" -p "$PORT" -d postgres -c "DROP DATABASE \"$STAGING_DB\";"
fi

# Clone the database using CREATE DATABASE WITH TEMPLATE
echo "Creating new database $STAGING_DB as a clone of $PROD_DB..."
psql -v ON_ERROR_STOP=1 -U "$ADMIN_USER" -h "$HOST" -p "$PORT" -d postgres <<-EOSQL
  CREATE DATABASE "$STAGING_DB" WITH TEMPLATE "$PROD_DB" OWNER "$STAGING_USER";
EOSQL

echo "Database cloning completed successfully."
