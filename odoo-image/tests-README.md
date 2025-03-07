# Helm Tests for Odoo Setup

This directory contains Helm tests that verify the correct functioning of both the Odoo production and staging setup processes.

## Available Tests

### Basic Tests

1. **test-chart-installed.yaml**: A basic test that always runs to verify that the Helm chart is installed correctly.

### Production Tests

These tests only run if a production database is configured (`.Values.odoo.database.name` is set):

1. **test-production-db.yaml**: Tests that the production database exists and is accessible.
2. **test-production-filestore.yaml**: Tests that the production filestore PVC has been created and bound.
3. **test-production-connectivity.yaml**: Tests that the production Odoo service is responding with a healthy status.

## Running the Tests

After installing or upgrading the Helm chart, you can run the tests using the following command:

```bash
helm test <release-name> -n <namespace>
```

For example:

```bash
helm test odoo -n odoo-production
```

## Test Results

The tests will output their results to the console. You can view the logs of each test pod using:

```bash
kubectl logs <test-pod-name> -n <namespace>
```

For example:

```bash
kubectl logs odoo-test-staging-db-staging1 -n odoo-production
```

## Troubleshooting

If a test fails, check the logs of the test pod for more information. You can also check the logs of the related jobs and pods:

- Odoo pod: `kubectl logs deployment/odoo-<hostname> -n <namespace>`
