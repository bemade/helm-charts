# Keycloak Helm Chart

A Helm chart for deploying Keycloak - Identity and Access Management on Kubernetes.

## Features

- High availability with multi-replica deployment
- Infinispan clustering via KUBE_PING
- External PostgreSQL database support
- Traefik IngressRoute integration
- cert-manager TLS certificates
- Prometheus metrics endpoint
- Health checks for Kubernetes

## Prerequisites

- Kubernetes 1.19+
- Helm 3.0+
- Traefik ingress controller
- cert-manager for TLS certificates
- External PostgreSQL database

## Installation

```bash
# Create namespace
kubectl create namespace keycloak

# Install with custom values
helm install keycloak ./keycloak \
  --namespace keycloak \
  --set keycloak.hostname=keycloak.example.com \
  --set keycloak.database.host=postgres-pgnative \
  --set keycloak.database.database=keycloak \
  --set secrets.databasePassword=your-db-password \
  --set secrets.adminPassword=your-admin-password
```

## Configuration

### Key Values

| Parameter | Description | Default |
|-----------|-------------|---------|
| `keycloak.replicas` | Number of replicas | `2` |
| `keycloak.hostname` | Hostname for ingress | `keycloak.example.com` |
| `keycloak.database.host` | PostgreSQL host | `postgres-pgnative` |
| `keycloak.database.database` | Database name | `keycloak` |
| `keycloak.database.username` | Database username | `keycloak` |
| `keycloak.features.metrics` | Enable Prometheus metrics | `true` |
| `keycloak.features.health` | Enable health endpoints | `true` |
| `keycloak.clustering.enabled` | Enable HA clustering | `true` |
| `keycloak.ingress.enabled` | Enable Traefik IngressRoute | `true` |
| `keycloak.ingress.clusterIssuer` | cert-manager ClusterIssuer | `letsencrypt-dns` |

### Using Existing Secrets

To use existing Kubernetes secrets for credentials:

```yaml
keycloak:
  database:
    existingSecret: "my-db-secret"
    existingSecretKeys:
      username: "username"
      password: "password"
  admin:
    existingSecret: "my-admin-secret"
    existingSecretKey: "admin-password"
```

### Resource Limits

```yaml
keycloak:
  resources:
    requests:
      cpu: 500m
      memory: 512Mi
    limits:
      cpu: 2
      memory: 2Gi
```

## Accessing Keycloak

After installation, access the admin console at:

```
https://<hostname>/admin
```

Login with the admin credentials configured during installation.

## Monitoring

If metrics are enabled, Prometheus can scrape metrics from:

```
http://<service>:9000/metrics
```

## Uninstallation

```bash
helm uninstall keycloak --namespace keycloak
```
