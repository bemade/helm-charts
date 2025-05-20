# Odoo OpenAPI Tool Server Helm Chart

This Helm chart deploys the Odoo OpenAPI Tool Server to a Kubernetes cluster.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.2.0+
- Access to an Odoo instance

## Installing the Chart

1. Add the Helm repository (if applicable)

2. Create a values file (e.g., `my-values.yaml`) with your configuration:

```yaml
# Required values
api:
  key: "your-secure-api-key"

odoo:
  url: "http://your-odoo-server:8069"
  db: "your-database"
  user: "admin"
  password: "your-odoo-password"

# Optional: Customize resources
resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 100m
    memory: 128Mi
```

3. Install the chart:

```bash
helm install odoo-openapi ./odoo-openapi -f my-values.yaml
```

## Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `1` |
| `image.repository` | Container image repository | `your-registry/odoo-openapi` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `image.tag` | Image tag | `latest` |
| `api.key` | API key for authenticating requests | `""` (required) |
| `api.host` | Host to bind the server to | `0.0.0.0` |
| `api.port` | Port to run the server on | `8000` |
| `odoo.url` | Odoo server URL | `http://odoo:8069` |
| `odoo.db` | Odoo database name | `odoo` |
| `odoo.user` | Odoo username | `admin` |
| `odoo.password` | Odoo user password | `""` (required) |
| `service.type` | Kubernetes service type | `ClusterIP` |
| `service.port` | Service port | `80` |
| `service.targetPort` | Target port | `8000` |
| `resources` | Resource requests/limits | `{}` |

## Upgrading

To upgrade the release with a new configuration:

```bash
helm upgrade odoo-openapi ./odoo-openapi -f my-values.yaml
```

## Uninstalling

To uninstall/delete the release:

```bash
helm delete odoo-openapi
```

## Security Considerations

- The API key provides full access to the Odoo instance. Keep it secure.
- The Odoo password is stored in a Kubernetes Secret.
- Consider using network policies to restrict access to the service.
- For production, use TLS termination at the ingress level.
