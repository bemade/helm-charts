#!/bin/sh
set -e

echo "Testing production server connectivity..."

# Debug information
echo "Checking DNS resolution for odoo-${PROD_HOSTNAME}"
getent hosts odoo-${PROD_HOSTNAME} || echo "Could not resolve hostname"

# Wait for the Odoo service to be ready
echo "Waiting for Odoo production service to be ready..."
RETRY_COUNT=0
MAX_RETRIES=12

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  # Use the health endpoint to check if Odoo is up using the service name
  RESPONSE=$(curl -s http://odoo-${PROD_HOSTNAME}:8069/web/health)
  
  if [ "$RESPONSE" = '{"status": "pass"}' ]; then
    echo "✅ Odoo production service is responding with healthy status."
    exit 0
  fi
  
  RETRY_COUNT=$((RETRY_COUNT+1))
  echo "Waiting for Odoo production service to be ready... ($RETRY_COUNT/$MAX_RETRIES)"
  sleep 5
done

echo "ERROR: Odoo production service did not become ready within the timeout period!"
exit 1
