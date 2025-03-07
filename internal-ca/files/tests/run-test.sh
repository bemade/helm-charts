#!/bin/bash
set -e

# No need to create RBAC resources - they're created by Helm

# Run the test script directly
echo "Running test script directly..."

# Run the test script with bash (no need to make it executable)
bash /files/tests/test-ca-certificate.sh

# No need to clean up RBAC resources - they'll be cleaned up by Helm

echo "Test completed successfully!"
