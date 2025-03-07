#!/bin/bash
set -e

# Environment variables passed to the container
HOST=${HOST}
PORT=${PORT}
ADMIN_USER=${ADMIN_USER}
ADMIN_PASSWORD=${ADMIN_PASSWORD}
RELEASE_NAMESPACE=${RELEASE_NAMESPACE}
RELEASE_NAME=${RELEASE_NAME}
CURRENT_USERS=${CURRENT_USERS}

echo "Cleaning up database users that are no longer needed..."

echo "Connecting to PostgreSQL at $HOST:$PORT as $ADMIN_USER"

# Get the list of current users from the database that match our naming pattern
DB_USERS=$(psql -t -v ON_ERROR_STOP=1 --host="$HOST" --port="$PORT" --username="$ADMIN_USER" --dbname="postgres" -c "SELECT usename FROM pg_catalog.pg_user WHERE usename LIKE '${RELEASE_NAMESPACE}-${RELEASE_NAME}-%';" | tr -d ' ')

# Convert the comma-separated list of current users to an array
IFS=',' read -ra CURRENT_USERS_ARRAY <<< "$CURRENT_USERS"

# For each database user that matches our pattern
for DB_USER in $DB_USERS; do
  # Check if the user is in our current list
  FOUND=false
  for CURRENT_USER in "${CURRENT_USERS_ARRAY[@]}"; do
    if [ "$DB_USER" == "$CURRENT_USER" ]; then
      FOUND=true
      break
    fi
  done
  
  # If the user is not in our current list, drop it
  if [ "$FOUND" == "false" ]; then
    echo "Dropping user $DB_USER as it's no longer needed..."
    
    psql -v ON_ERROR_STOP=1 --host="$HOST" --port="$PORT" --username="$ADMIN_USER" --dbname="postgres" <<-EOSQL
    DO \$\$
    BEGIN
      -- Drop all objects owned by the user
      DROP OWNED BY "$DB_USER";
      
      -- Drop the user
      DROP USER "$DB_USER";
      
      RAISE NOTICE 'User $DB_USER has been dropped';
    END
    \$\$;
EOSQL
  else
    echo "User $DB_USER is still needed, keeping it."
  fi
done

echo "Cleanup of removed users completed."
