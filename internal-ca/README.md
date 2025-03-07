# Internal CA Helm Chart

This Helm chart creates a self-signed Certificate Authority (CA) for use with cert-manager in Kubernetes. It's designed to provide a simple way to create and manage internal certificates for services that don't need public trust.

## Features

- Creates a self-signed issuer
- Creates a CA certificate
- Supports both cluster-wide and namespace-scoped issuers

## Installation

```bash
helm install internal-ca ./internal-ca
```

## Configuration

| Parameter | Description | Default |
|-----------|-------------|----------|
| `ca.name` | Name of the CA | `"internal-ca"` |
| `ca.namespace` | Namespace where the CA will be created | `"cert-manager"` |
| `ca.commonName` | Common name for the CA | `"Internal Certificate Authority"` |
| `ca.duration` | Duration of the CA certificate | `"87600h"` (10 years) |
| `ca.clusterWide` | Whether the CA is a ClusterIssuer | `true` |

## Usage

Once installed, you can use the CA issuer to sign certificates:

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: example-cert
  namespace: default
spec:
  secretName: example-cert
  dnsNames:
    - example.svc.cluster.local
  issuerRef:
    name: internal-ca-issuer
    kind: ClusterIssuer
```
