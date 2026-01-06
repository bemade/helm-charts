# Bemade Helm Charts

Helm charts for deploying Bemade infrastructure on Kubernetes.

## Available Charts

| Chart | Description | Version |
|-------|-------------|---------|
| [odoo-operator](./odoo-operator/) | Kubernetes operator for managing Odoo instances | 0.8.0 |
| [odoo-instance](./odoo-instance/) | Deploy a single OdooInstance CR | 0.1.0 |
| [internal-ca](./internal-ca/) | Internal Certificate Authority with cert-manager | - |
| [odoo-openapi](./odoo-openapi/) | OpenAPI proxy for Odoo | - |
| [onlyoffice](./onlyoffice/) | OnlyOffice document server | 1.0.0 |

## Quick Start

### Add the Repository

```bash
helm repo add bemade https://bemade.github.io/helm-charts
helm repo update
```

### Install the Odoo Operator

```bash
helm install odoo-operator bemade/odoo-operator \
  --namespace odoo-operator \
  --create-namespace \
  --set database.host=postgres.default.svc
```

### Create an Odoo Instance

```bash
helm install my-odoo bemade/odoo-instance \
  --namespace default \
  --set instance.name=my-odoo \
  --set instance.ingress.hosts[0]=my-odoo.example.com
```

## Repository Structure

Each helm chart is contained in a subfolder of this repository. In order to
function correctly, each helm chart folder must contain a `Chart.yaml` and a
`values.yaml` file at its root. It should also contain a variety of Kubernetes
resource templates in a `templates` subdirectory.

## Development

### Testing Charts Locally

```bash
# Lint a chart
helm lint ./odoo-operator

# Template a chart (dry-run)
helm template my-release ./odoo-operator -f testing/odoo-operator/values.yaml

# Install with debug
helm install my-release ./odoo-operator --debug --dry-run
```

### Packaging Charts

```bash
helm package ./odoo-operator
helm repo index . --url https://bemade.github.io/helm-charts
```

## Documentation

- [Helm Chart Template Guide](https://helm.sh/docs/chart_template_guide/)
- [Odoo Operator Documentation](./odoo-operator/README.md)

## License

LGPL-v3: https://www.gnu.org/licenses/lgpl-3.0.en.html 
