# Bemade Helm Charts

Helm charts for deploying Bemade infrastructure on Kubernetes.

## Available Charts

| Chart | Description | Version |
|-------|-------------|---------|
| [odoo-operator](./odoo-operator/) | Kubernetes operator for managing Odoo instances | 0.11.0 |
| [odoo-instance](./odoo-instance/) | Deploy a single OdooInstance CR | 0.4.0 |
| [postgres-pgvector](./postgres-pgvector/) | Single-instance PostgreSQL with pgvector extension | 0.1.0 |
| [minio](./minio/) | Minimal MinIO deployment with ingress | 0.1.0 |
| [internal-ca](./internal-ca/) | Internal Certificate Authority with cert-manager | 0.1.0 |
| [odoo-openapi](./odoo-openapi/) | OpenAPI proxy for Odoo | 0.1.3 |
| [onlyoffice](./onlyoffice/) | OnlyOffice document server | 1.0.0 |

## Quick Start

### Add the Repository

```bash
helm repo add bemade https://bemade.github.io/helm-charts
helm repo update
```

### Install the Odoo Operator

First, create a secret containing your PostgreSQL cluster configuration:

```bash
cat > clusters.yaml << EOF
main:
  host: "postgres.database.svc.cluster.local"
  port: 5432
  adminUser: "postgres"
  adminPassword: "your-secure-password"
  default: true
EOF

kubectl create namespace odoo-operator
kubectl create secret generic postgres-clusters -n odoo-operator \
  --from-file=clusters.yaml=clusters.yaml
```

Then install the operator:

```bash
helm install odoo-operator bemade/odoo-operator \
  --namespace odoo-operator \
  --set postgresClustersSecretRef.name=postgres-clusters
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
helm repo index . --url https://bemade.github.io/helm-charts/
```

## Documentation

- [Helm Chart Template Guide](https://helm.sh/docs/chart_template_guide/)
- [Odoo Operator Documentation](./odoo-operator/README.md)

## License

This project is licensed under the GNU Lesser General Public License v3.0 - see the [LICENSE](LICENSE) file for details. 
