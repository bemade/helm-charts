# Changelog

This Helm-Chart increase there major version on every breaking change (or major version of Nextcloud itself) inspired by semantic releases.

Here we list all major versions and their breaking changes for migration.

## 1.0.21
- **Fix**: init-nextcloud-files now always copies source files when version.php is missing, regardless of fresh install or existing DB. Previously, fresh installs skipped the copy relying on Docker entrypoint, but PVC subPath mounts shadow the image files causing empty /var/www/html and CrashLoopBackOff.
- **Fix**: init container now sets correct www-data ownership on config/ directory and CAN_INSTALL file.
- **Change**: startupProbe enabled by default (initialDelay=5s, failureThreshold=30, period=10s = 5min grace) to prevent liveness probe from killing pods during first-time Nextcloud installation.

## v9
- upgrade to v33 major version
- move `metrics.serviceMonitor` to `prometheus.serviceMonitor`: It us used for metrics like openmetric and nextcloud-exporter
- move `metrics.rules` to `prometheus.rules`: It us used for all collected metrics

## v8
- `cronjob.command` was renamed to `cronjob.sidecar.command` to avoid confusion with the cronjob command. Please update your `values.yaml` accordingly.

## v7

- update redis to v20 (see [CHANGELOG](https://github.com/bitnami/charts/blob/main/bitnami/redis/CHANGELOG.md#2000-2024-08-09))
- update redis to v21 (see [CHANGELOG](https://github.com/bitnami/charts/blob/main/bitnami/redis/CHANGELOG.md#2100-2025-05-06)
- update postgresql to v16 (see [CHANGELOG](https://github.com/bitnami/charts/blob/main/bitnami/postgresql/CHANGELOG.md#1600-2024-10-02))
    - maybe use [pgautoupgrade](https://github.com/pgautoupgrade/docker-pgautoupgrade) to update to v17 (helm v16), with:
      ```yaml
      postgresql:
        primary:
          initContainers:
            - name: upgrade
              image: "pgautoupgrade/pgautoupgrade:17-alpine"
              env:
                - name: "PGAUTO_ONESHOT"
                  value: "yes"
              volumeMounts:
                - mountPath: "/bitnami/postgresql"
                  name: "data"
      ```
- update mariadb to v19 (see [CHANGELOG](https://github.com/bitnami/charts/blob/main/bitnami/mariadb/CHANGELOG.md#1900-2024-07-11))
- update mariadb to v20 (see [CHANGELOG](https://github.com/bitnami/charts/blob/main/bitnami/mariadb/CHANGELOG.md#2000-2024-11-08))
- update nextcloud to v31 (see [CHANGELOG](https://nextcloud.com/changelog/#31-0-0))
