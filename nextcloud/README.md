# Nextcloud Helm Chart

A Helm chart for deploying Nextcloud on Kubernetes with Traefik ingress.

## Why this chart?

This chart is a simplified alternative to the official Nextcloud Helm chart, specifically designed to work with **Rancher**. The official chart uses YAML keys with dots (e.g., `apache-pretty-urls.config.php: true`) which Rancher's UI incorrectly interprets as nested paths, causing deployment failures.

This chart:
- Uses only simple YAML keys (no dots in key names)
- Manages PHP configuration via ConfigMaps
- Passes Nextcloud options via environment variables

## Features

- External PostgreSQL database support
- Traefik IngressRoute with TLS (cert-manager)
- S3 object storage support (optional)
- Redis caching support (optional)
- SMTP email configuration
- CronJob for background tasks
- Large file upload support (16GB default)

## Prerequisites

- Kubernetes 1.19+
- Helm 3.0+
- Traefik ingress controller
- cert-manager for TLS certificates
- External PostgreSQL database

## Installation

```bash
# Create namespace
kubectl create namespace nextcloud

# Install with custom values
helm install nextcloud ./nextcloud \
  --namespace nextcloud \
  --set nextcloud.hostname=nextcloud.example.com \
  --set database.host=postgres-pgnative \
  --set database.name=nextcloud \
  --set secrets.adminPassword=your-admin-password \
  --set secrets.databasePassword=your-db-password
```

## Configuration

### Key Values

| Parameter | Description | Default |
|-----------|-------------|---------|
| `nextcloud.hostname` | Hostname for ingress | `nextcloud.example.com` |
| `nextcloud.admin.username` | Admin username | `admin` |
| `nextcloud.replicas` | Number of replicas | `1` |
| `nextcloud.persistence.size` | Storage size | `10Gi` |
| `database.host` | PostgreSQL host | `postgres-pgnative` |
| `database.name` | Database name | `nextcloud` |
| `redis.enabled` | Enable Redis caching | `false` |
| `cronjob.enabled` | Enable background jobs | `true` |

### PHP Configuration

```yaml
nextcloud:
  phpConfig:
    memoryLimit: "512M"
    uploadMaxFilesize: "16G"
    postMaxSize: "16G"
    maxExecutionTime: "3600"
```

### S3 Object Storage

```yaml
nextcloud:
  objectStore:
    s3:
      enabled: true
      host: "minio.example.com"
      bucket: "nextcloud"
      region: "us-east-1"
      usePathStyle: true
secrets:
  s3AccessKey: "your-access-key"
  s3SecretKey: "your-secret-key"
```

### Redis Caching

```yaml
redis:
  enabled: true
  host: "redis-master"
  port: 6379
secrets:
  redisPassword: "your-redis-password"
```

### Using Existing Secrets

```yaml
nextcloud:
  admin:
    existingSecret: "my-nextcloud-secret"
    existingSecretKeys:
      username: "nextcloud-username"
      password: "nextcloud-password"
database:
  existingSecret: "my-db-secret"
  existingSecretKeys:
    username: "db-username"
    password: "db-password"
```

## Post-Installation

After installation, access Nextcloud at:

```
https://<hostname>
```

### Enable Pretty URLs

Run this command in the Nextcloud pod to enable pretty URLs:

```bash
kubectl exec -it -n nextcloud deploy/nextcloud -- su -s /bin/bash www-data -c "php occ maintenance:update:htaccess"
```

## Uninstallation

```bash
helm uninstall nextcloud --namespace nextcloud
```
