# Odoo Operator for Kubernetes

The Odoo Operator is a Kubernetes operator that simplifies the deployment and management of Odoo instances in a Kubernetes cluster. It follows the operator pattern, allowing users to define Odoo instances as custom resources that the operator will reconcile.

## Features

- **Declarative Odoo Instance Management**: Define your Odoo instances as Kubernetes resources
- **Automated Deployment**: The operator handles the creation of all necessary Kubernetes resources
- **Storage Management**: Automatic configuration of persistent volumes for filestore
- **Database Management**: Automatic creation and management of database users and databases
- **Secret Management**: Support for instance-specific admin secrets
- **Addon Management**: Easily add custom addons from Git repositories
- **Ingress Configuration**: Automatic setup of ingress resources for web access

## Implementation

The Odoo Operator is implemented in Python using the [Kopf](https://github.com/nolar/kopf) framework, which provides a high-level API for creating Kubernetes operators. This makes the operator easy to understand, maintain, and extend.

## Installation

### Prerequisites

- Kubernetes 1.19+
- Helm 3.2.0+
- A storage class for persistent volumes

### Installing the Operator

```bash
helm repo add bemade https://charts.bemade.org
helm repo update
helm install odoo-operator bemade/odoo-operator
```

Or install from local chart:

```bash
cd odoo-operator
helm install odoo-operator ./odoo-operator
```

## Usage

### Creating an Odoo Instance

Create a YAML file with your Odoo instance definition:

```yaml
apiVersion: odoo.bemade.org/v1
kind: OdooInstance
metadata:
  name: demo
  namespace: default
spec:
  version: "17.0"
  replicas: 1
  # Optional: Specify an admin secret for this instance
  adminSecret:
    name: "demo-admin-secret"
    key: "admin-password"
  resources:
    limits:
      cpu: "2"
      memory: "4Gi"
    requests:
      cpu: "500m"
      memory: "1Gi"
  filestore:
    storageSize: "20Gi"
    storageClass: "standard"
  ingress:
    enabled: true
    hostname: "demo.odoo.example.com"
    tls: true
```

Apply it to your cluster:

```bash
kubectl apply -f odoo-instance.yaml
```

### Adding Custom Addons

You can specify Git repositories to clone and use as Odoo addons:

```yaml
spec:
  # ... other fields ...
  addons:
    - repo: "https://github.com/OCA/web"
      branch: "17.0"
    - repo: "https://github.com/bemade/custom-addons"
      branch: "main"
```

### Checking the Status

```bash
kubectl get odooinstances
kubectl describe odooinstance demo
```

## Configuration

See the [values.yaml](./odoo-operator/values.yaml) file for the complete list of configuration options.

## Architecture

The Odoo Operator follows the Kubernetes operator pattern, using controllers to watch for changes to custom resources and reconciling the actual state with the desired state.

### Components

- **Custom Resource Definitions (CRDs)**: Define the schema for Odoo resources
- **Kopf Handlers**: Python functions that handle create, update, and delete events for Odoo resources
- **Kubernetes API Clients**: Used to create and manage Kubernetes resources

## Development

### Local Development

```bash
# Clone the repository
git clone https://github.com/bemade/helm-charts.git
cd helm-charts/odoo-operator

# Install dependencies
pip install -r python/requirements.txt

# Run tests
python -m pytest python/tests

# Run the operator locally
kopf run python/operator.py --verbose
```

### Building the Docker Image

```bash
make docker-build
```

### Installing the Operator

```bash
# Install CRDs
kubectl apply -f odoo-operator/templates/crds/

# Install the chart
helm install odoo-operator ./odoo-operator
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- The Kubernetes community for the operator pattern
- The Kopf framework for making it easy to create Kubernetes operators in Python
- The Odoo community for the excellent ERP system
