#!/bin/sh
set -e

echo "Testing that the Helm chart is installed correctly..."

# Check if the namespace exists
echo "Checking if namespace ${NAMESPACE} exists..."
kubectl get namespace ${NAMESPACE} > /dev/null
if [ $? -ne 0 ]; then
  echo "ERROR: Namespace ${NAMESPACE} does not exist!"
  exit 1
fi
echo "✅ Namespace ${NAMESPACE} exists."

# Check if the ConfigMap exists
echo "Checking if ConfigMap test-scripts exists..."
kubectl get configmap test-scripts -n ${NAMESPACE} > /dev/null
if [ $? -ne 0 ]; then
  echo "ERROR: ConfigMap test-scripts does not exist!"
  exit 1
fi
echo "✅ ConfigMap test-scripts exists."

echo "All tests passed! Helm chart is installed correctly."
exit 0
