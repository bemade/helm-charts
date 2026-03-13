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

### Using a Values File

For production, use a dedicated values file (recommended):

```bash
helm install openclaw bemade/openclaw \
  --namespace openclaw \
  -f values-openclaw.yaml
```

### Using External Secrets

You can also create the Kubernetes Secret manually:

```bash
kubectl create secret generic openclaw-secrets \
  --namespace openclaw \
  --from-literal=ANTHROPIC_API_KEY=sk-ant-xxxxx \
  --from-literal=OPENCLAW_GATEWAY_TOKEN=your-gateway-token \
  --from-literal=TELEGRAM_BOT_TOKEN=your-bot-token

# Install without secrets in values
helm install openclaw bemade/openclaw \
  --namespace openclaw \
  --set openclaw.hostname=openclaw.example.com
```

## Configuration

### General

| Parameter | Description | Default |
|-----------|-------------|---------|
| `nameOverride` | Override chart name | `""` |
| `fullnameOverride` | Override full release name | `""` |
| `openclaw.image.repository` | Docker image repository | `ghcr.io/openclaw/openclaw` |
| `openclaw.image.tag` | Docker image tag | `latest` |
| `openclaw.image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `openclaw.port` | Gateway port | `18789` |
| `openclaw.hostname` | Hostname for ingress | `openclaw.example.com` |
| `openclaw.command` | Container command | `["node", "/app/openclaw.mjs"]` |
| `openclaw.args` | Container args (empty = auto with port) | `[]` |

### Ingress & TLS

| Parameter | Description | Default |
|-----------|-------------|---------|
| `openclaw.ingress.enabled` | Enable Traefik IngressRoute | `true` |
| `openclaw.ingress.clusterIssuer` | cert-manager ClusterIssuer | `letsencrypt-dns` |
| `openclaw.ingress.hsts.enabled` | Enable HSTS header | `true` |
| `openclaw.ingress.hsts.maxAge` | HSTS max-age in seconds | `15552000` |
| `openclaw.ingress.hsts.includeSubdomains` | HSTS include subdomains | `true` |
| `openclaw.ingress.hsts.preload` | HSTS preload | `true` |

### Resources & Scheduling

| Parameter | Description | Default |
|-----------|-------------|---------|
| `openclaw.resources.requests.cpu` | CPU request | `500m` |
| `openclaw.resources.requests.memory` | Memory request | `512Mi` |
| `openclaw.resources.limits.cpu` | CPU limit | `2` |
| `openclaw.resources.limits.memory` | Memory limit | `2Gi` |
| `openclaw.nodeSelector` | Node selector | `{}` |
| `openclaw.tolerations` | Tolerations | `[]` |
| `openclaw.podAnnotations` | Pod annotations | `{}` |

### Persistence

| Parameter | Description | Default |
|-----------|-------------|---------|
| `openclaw.persistence.enabled` | Enable persistent storage | `true` |
| `openclaw.persistence.storageClass` | Storage class | `""` |
| `openclaw.persistence.size` | PVC size | `5Gi` |

### Health Probes

| Parameter | Description | Default |
|-----------|-------------|---------|
| `openclaw.probes.liveness.path` | Liveness probe path | `/health` |
| `openclaw.probes.liveness.initialDelaySeconds` | Liveness initial delay | `30` |
| `openclaw.probes.liveness.periodSeconds` | Liveness period | `10` |
| `openclaw.probes.readiness.path` | Readiness probe path | `/health` |
| `openclaw.probes.readiness.initialDelaySeconds` | Readiness initial delay | `5` |
| `openclaw.probes.readiness.periodSeconds` | Readiness period | `5` |

### OpenClaw Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `openclaw.config` | Full `openclaw.json` content (mounted as ConfigMap) | See `values.yaml` |

The `config` block is serialized as `openclaw.json` and mounted into the container.
See the [Configuration Reference](https://docs.openclaw.ai/gateway/configuration-reference) for all options.

> **Note**: The pod is automatically restarted when the config changes (via `config-hash` annotation).

### Secrets

Built-in secrets are mapped to their standard environment variables:

| Parameter | Env var | Description |
|-----------|---------|-------------|
| `openclaw.secrets.anthropicApiKey` | `ANTHROPIC_API_KEY` | Anthropic API key |
| `openclaw.secrets.openaiApiKey` | `OPENAI_API_KEY` | OpenAI API key |
| `openclaw.secrets.gatewayToken` | `OPENCLAW_GATEWAY_TOKEN` | Gateway auth token |

#### Extra Secrets

Use `openclaw.secrets.extra` for any additional secret environment variable.
The key is the exact env var name, the value is the secret:

```yaml
openclaw:
  secrets:
    extra:
      TELEGRAM_BOT_TOKEN: "123456:ABC-DEF..."
      OPENROUTER_API_KEY: "sk-or-..."
      GROQ_API_KEY: "gsk_..."
      GOOGLE_API_KEY: "AIza..."
      OPENCLAW_GATEWAY_PASSWORD: "my-password"
```

All secrets are stored in a single Kubernetes Secret and injected as env vars.
OpenClaw reads API keys from env vars automatically
(see [Environment Variables](https://docs.openclaw.ai/help/environment)).

#### Extra Environment Variables

Use `openclaw.extraEnv` for non-secret env vars:

```yaml
openclaw:
  extraEnv:
    OPENCLAW_LOG_LEVEL: "debug"
    OPENCLAW_DISABLE_BONJOUR: "1"
```

## Accessing the Control UI

After installation, access the Control UI at `https://<hostname>/`.

Use the gateway token to authenticate in Settings → Token.

## Supported AI Models

OpenClaw supports multiple AI providers:

- **Anthropic**: `anthropic/claude-opus-4-6`, `anthropic/claude-sonnet-4-20250514`
- **OpenAI**: `openai/gpt-4o`, `openai/gpt-4-turbo`
- **Ollama**: `ollama/llama3`, `ollama/glm-5:cloud`, etc.
- **OpenRouter**: any model via `openrouter/...`
- **Groq**: `groq/llama-3.1-70b-versatile`, etc.
- See [Models documentation](https://docs.openclaw.ai/concepts/models) for more options

## Documentation

- [OpenClaw Documentation](https://docs.openclaw.ai/)
- [Configuration Reference](https://docs.openclaw.ai/gateway/configuration-reference)
- [Environment Variables](https://docs.openclaw.ai/help/environment)
- [Security Guide](https://docs.openclaw.ai/gateway/security)
