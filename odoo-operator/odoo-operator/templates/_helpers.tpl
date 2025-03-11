{{/*
Expand the name of the chart.
*/}}
{{- define "odoo-operator.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "odoo-operator.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "odoo-operator.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "odoo-operator.labels" -}}
helm.sh/chart: {{ include "odoo-operator.chart" . }}
{{ include "odoo-operator.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "odoo-operator.selectorLabels" -}}
app.kubernetes.io/name: {{ include "odoo-operator.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "odoo-operator.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "odoo-operator.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Get the CA bundle from the internal-ca secret
*/}}
{{- define "odoo-operator.caBundle" -}}
{{- $caName := .Values.webhook.cert.issuerRef.name | trimSuffix "-issuer" -}}
{{- $caNamespace := .Values.webhook.cert.caNamespace | default .Release.Namespace -}}
{{- $caSecret := lookup "v1" "Secret" $caNamespace $caName -}}
{{- if $caSecret -}}
{{- if hasKey $caSecret.data "ca.crt" -}}
{{- index $caSecret.data "ca.crt" -}}
{{- else if hasKey $caSecret.data "tls.crt" -}}
{{- index $caSecret.data "tls.crt" -}}
{{- else -}}
{{- fail (printf "Secret %s in namespace %s does not contain ca.crt or tls.crt" $caName $caNamespace) -}}
{{- end -}}
{{- else -}}
{{- fail (printf "Secret %s not found in namespace %s" $caName $caNamespace) -}}
{{- end -}}
{{- end -}}
