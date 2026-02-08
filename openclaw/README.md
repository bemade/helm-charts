# OpenClaw Helm Chart

A Helm chart for deploying [OpenClaw](https://github.com/openclaw/openclaw) - Your personal AI assistant.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.0+
- Traefik ingress controller
- cert-manager (for TLS certificates)

## Installation

### Add the Repository

```bash
helm repo add bemade https://git.bemade.org/bemade/helm-charts/-/raw/main/
helm repo update
```

### Install the Chart

```bash
# Create namespace
kubectl create namespace openclaw

# Install with API keys
helm install openclaw bemade/openclaw \
  --namespace openclaw \
  --set openclaw.hostname=openclaw.example.com \
  --set openclaw.secrets.anthropicApiKey=sk-ant-xxxxx \
  --set openclaw.secrets.gatewayToken=your-gateway-token
```

### Using External Secrets

For production, it's recommended to use external secret management:

```bash
# Create secret manually
kubectl create secret generic openclaw-secrets \
  --namespace openclaw \
  --from-literal=anthropic-api-key=sk-ant-xxxxx \
  --from-literal=gateway-token=your-gateway-token

# Install without secrets in values
helm install openclaw bemade/openclaw \
  --namespace openclaw \
  --set openclaw.hostname=openclaw.example.com
```

## Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `openclaw.image.repository` | Docker image repository | `ghcr.io/openclaw/openclaw` |
| `openclaw.image.tag` | Docker image tag | `latest` |
| `openclaw.image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `openclaw.port` | Gateway port | `18789` |
| `openclaw.hostname` | Hostname for ingress | `openclaw.example.com` |
| `openclaw.ingress.enabled` | Enable ingress | `true` |
| `openclaw.ingress.clusterIssuer` | cert-manager ClusterIssuer | `letsencrypt-dns` |
| `openclaw.resources.requests.cpu` | CPU request | `500m` |
| `openclaw.resources.requests.memory` | Memory request | `512Mi` |
| `openclaw.resources.limits.cpu` | CPU limit | `2` |
| `openclaw.resources.limits.memory` | Memory limit | `2Gi` |
| `openclaw.persistence.enabled` | Enable persistent storage | `true` |
| `openclaw.persistence.storageClass` | Storage class | `""` |
| `openclaw.persistence.size` | PVC size | `5Gi` |
| `openclaw.config.agent.model` | AI model to use | `anthropic/claude-sonnet-4-20250514` |
| `openclaw.secrets.anthropicApiKey` | Anthropic API key | `""` |
| `openclaw.secrets.openaiApiKey` | OpenAI API key | `""` |
| `openclaw.secrets.gatewayToken` | Gateway token for Control UI | `""` |

## Accessing the Control UI

After installation, access the Control UI at `https://<hostname>/`.

Use the gateway token to authenticate in Settings → Token.

## Supported AI Models

OpenClaw supports multiple AI providers:

- **Anthropic**: `anthropic/claude-opus-4-6`, `anthropic/claude-sonnet-4-20250514`
- **OpenAI**: `openai/gpt-4o`, `openai/gpt-4-turbo`
- See [Models documentation](https://docs.openclaw.ai/concepts/models) for more options

## Documentation

- [OpenClaw Documentation](https://docs.openclaw.ai/)
- [Configuration Reference](https://docs.openclaw.ai/gateway/configuration)
- [Security Guide](https://docs.openclaw.ai/gateway/security)
