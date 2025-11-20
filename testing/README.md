# Kubernetes Dev/Test Environment

This folder contains helpers for spinning up a local Kubernetes environment in Minikube for working on the Odoo operator and related charts.

## Contents

- `build-test-env.sh`
- `postgres.yaml`
- sub-folders for testing specific charts

## Prerequisites

- Ubuntu 24.04 (or similar Linux)
- `sudo` access
- Nothing else required: the script will install `kubectl`, `helm`, and `minikube` if missing.

## 1. Create / refresh the local cluster

From the repo root:

```bash
cd helm-charts/testing
./build-test-env.sh
```

This will:

- Ensure Minikube default profile (`minikube`) is running (driver defaults to `docker`).
- Install / upgrade:
  - Traefik (as an Ingress controller, `LoadBalancer` service) in `traefik` namespace.
  - cert-manager (with CRDs) in `cert-manager` namespace.
  - Zalando Postgres Operator in `postgres-operator` namespace.
- Apply `postgres.yaml`:
  - Namespace `postgres` with a simple PostgreSQL `Deployment` + `Service`.
  - Namespace `odoo-operator` with a `postgres-admin` secret used by the operator.
  - A simple single-node PostgreSQL server running in the `postgres` namespace.

## 2. Install the Odoo operator (chart from this repo)

From the `helm-charts` root:

```bash
cd ..   # from helm-charts/testing to helm-charts
helm upgrade --install odoo-operator odoo-operator \
  -n odoo-operator \
  --create-namespace \
  -f testing/odoo-operator/values.yaml
```

This deploys the operator into namespace `odoo-operator` and configures it to use the test PostgreSQL instance.

## 3. Create a test Odoo instance

Still from `helm-charts` root:

```bash
helm upgrade --install test-odoo-instance odoo-instance \
  -n odoo-operator \
  -f testing/odoo-instance/values.yaml
```

This creates an `OdooInstance` custom resource which the operator will reconcile into a running Odoo Deployment, Service and Traefik ingress routes.

## 4. Expose Traefik via Minikube tunnel

Because Traefik uses a `LoadBalancer` service, run Minikube's tunnel in another terminal:

```bash
minikube tunnel -p minikube
```

Leave this running. Then check the Traefik service:

```bash
kubectl -n traefik get svc traefik
```

You should see a non-`<pending>` `EXTERNAL-IP` (often `127.0.0.1` or a local IP). Use that IP on ports 80/443 to reach Odoo, with the hostnames defined in `testing/odoo-instance/values.yaml` (e.g. `test.odoo.local`).

Example `/etc/hosts` entry:

```text
127.0.0.1   test.odoo.local
```

Then open:

- `http://test.odoo.local`
- or `https://test.odoo.local` (will use self-signed certs issued by cert-manager).

## 5. Useful commands

- Check operator status:

```bash
kubectl -n odoo-operator get pods
kubectl -n odoo-operator logs deploy/odoo-operator
```

- List Odoo instances:

```bash
kubectl get odoo -A
```

- Check Postgres:

```bash
kubectl -n postgres get pods,svc
```

## 6. Teardown

To remove test resources but keep the cluster:

```bash
helm uninstall test-odoo-instance -n odoo-operator || true
helm uninstall odoo-operator -n odoo-operator || true
kubectl delete -f testing/postgres.yaml || true
```

To delete the whole Minikube cluster:

```bash
minikube delete -p minikube
```
