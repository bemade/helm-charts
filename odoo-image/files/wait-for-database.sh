#!/bin/bash
set -e

# Environment variables
DB_NAME=${DB_NAME}
DB_HOST=${DB_HOST}
DB_PORT=${DB_PORT}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
MAX_RETRIES=${MAX_RETRIES:-60}
RETRY_INTERVAL=${RETRY_INTERVAL:-10}
CHECK_NEUTRALIZED=${CHECK_NEUTRALIZED:-true}

echo "Waiting for database ${DB_NAME} to be ready and neutralized..."

# Install PostgreSQL client
apk add --no-cache postgresql-client

# Function to check if database exists
check_database_exists() {
  PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d postgres -t -c "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1
  return $?
}

# Function to check if database has been neutralized
check_database_neutralized() {
  if [ "${CHECK_NEUTRALIZED}" != "true" ]; then
    # Skip neutralization check if not required
    return 0
  fi
  
  # Check if the ir_config_parameter table exists (database is initialized)
  table_exists=$(PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} -t -c "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'ir_config_parameter')" 2>/dev/null || echo "f")
  
  if [ "$table_exists" = " t" ]; then
    # Check if the database has been neutralized
    PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} -t -c "SELECT 1 FROM ir_config_parameter WHERE key='database.is_neutralized' AND value='true'" | grep -q 1
    return $?
  else
    # Table doesn't exist yet, database is not ready
    return 1
  fi
}

# Wait for the database to be ready and neutralized
retry_count=0
while [ ${retry_count} -lt ${MAX_RETRIES} ]; do
  # First check if database exists
  if check_database_exists; then
    echo "Database ${DB_NAME} exists, checking if it's neutralized..."
    
    # Then check if it's neutralized
    if check_database_neutralized; then
      echo "Database ${DB_NAME} is ready and neutralized!"
      exit 0
    else
      echo "Database ${DB_NAME} exists but is not neutralized yet."
    fi
  else
    echo "Database ${DB_NAME} does not exist yet."
  fi
  
  retry_count=$((retry_count+1))
  echo "Waiting for database to be ready and neutralized. Retry ${retry_count}/${MAX_RETRIES} in ${RETRY_INTERVAL} seconds..."
  sleep ${RETRY_INTERVAL}
done

echo "Timed out waiting for database ${DB_NAME} to be ready and neutralized after ${MAX_RETRIES} attempts."
exit 1
