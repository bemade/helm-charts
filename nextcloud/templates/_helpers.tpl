{{/*
Expand the name of the chart.
*/}}
{{- define "nextcloud.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "nextcloud.fullname" -}}
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
{{- define "nextcloud.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "nextcloud.labels" -}}
helm.sh/chart: {{ include "nextcloud.chart" . }}
{{ include "nextcloud.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "nextcloud.selectorLabels" -}}
app.kubernetes.io/name: {{ include "nextcloud.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "nextcloud.serviceAccountName" -}}
{{- if .Values.nextcloud.serviceAccount.create }}
{{- default (include "nextcloud.fullname" .) .Values.nextcloud.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.nextcloud.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Database secret name
*/}}
{{- define "nextcloud.databaseSecretName" -}}
{{- if .Values.database.existingSecret }}
{{- .Values.database.existingSecret }}
{{- else }}
{{- include "nextcloud.fullname" . }}-db
{{- end }}
{{- end }}

{{/*
Admin secret name
*/}}
{{- define "nextcloud.adminSecretName" -}}
{{- if .Values.nextcloud.admin.existingSecret }}
{{- .Values.nextcloud.admin.existingSecret }}
{{- else }}
{{- include "nextcloud.fullname" . }}-admin
{{- end }}
{{- end }}

{{/*
SMTP secret name
*/}}
{{- define "nextcloud.smtpSecretName" -}}
{{- if .Values.nextcloud.mail.smtp.existingSecret }}
{{- .Values.nextcloud.mail.smtp.existingSecret }}
{{- else }}
{{- include "nextcloud.fullname" . }}-smtp
{{- end }}
{{- end }}

{{/*
S3 secret name
*/}}
{{- define "nextcloud.s3SecretName" -}}
{{- if .Values.nextcloud.objectStore.s3.existingSecret }}
{{- .Values.nextcloud.objectStore.s3.existingSecret }}
{{- else }}
{{- include "nextcloud.fullname" . }}-s3
{{- end }}
{{- end }}

{{/*
Redis secret name
*/}}
{{- define "nextcloud.redisSecretName" -}}
{{- if .Values.redis.existingSecret }}
{{- .Values.redis.existingSecret }}
{{- else }}
{{- include "nextcloud.fullname" . }}-redis
{{- end }}
{{- end }}

{{/*
Trusted domains as comma-separated string
*/}}
{{- define "nextcloud.trustedDomains" -}}
{{- $domains := list .Values.nextcloud.hostname }}
{{- $domains = concat $domains .Values.nextcloud.trustedDomains }}
{{- join " " $domains }}
{{- end }}
