#!/bin/bash
set -e

# Environment variables passed to the container
echo "Dropping user $USER_TO_DROP if exists..."

echo "Connecting to PostgreSQL at $HOST:$PORT as $ADMIN_USER"

# First revoke all privileges and reassign owned objects
PGPASSWORD="$ADMIN_PASSWORD"; psql -v ON_ERROR_STOP=1 --host="$HOST" --port="$PORT" --username="$ADMIN_USER" --dbname="postgres" <<-EOSQL
DO \$\$
BEGIN
  IF EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = '$USER_TO_DROP') THEN
    -- Drop all objects owned by the user
    DROP OWNED BY "$USER_TO_DROP";
    
    -- Drop the user
    DROP USER "$USER_TO_DROP";
    
    RAISE NOTICE 'User $USER_TO_DROP has been dropped';
  ELSE
    RAISE NOTICE 'User $USER_TO_DROP does not exist, nothing to do';
  END IF;
END
\$\$;
EOSQL

echo "Cleanup completed."
