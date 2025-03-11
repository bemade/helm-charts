#!/usr/bin/env python3
"""
Odoo Operator - Kubernetes operator for managing Odoo instances

This operator manages the lifecycle of Odoo instances in a Kubernetes cluster.
It handles the creation, update, and deletion of all resources needed for an Odoo instance.
"""
import os
import kopf
import kubernetes.client as k8s
from kubernetes.client.rest import ApiException
import yaml
import logging
from typing import Dict, Any, List, Optional, Tuple
import json
import base64
from http import HTTPStatus
from flask import Flask, request, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("odoo-operator")

# Constants
GROUP = 'odoo.bemade.org'
VERSION = 'v1'
PLURAL = 'odooinstances'

# Get default values from environment variables
DEFAULT_ODOO_IMAGE = os.environ.get('DEFAULT_ODOO_IMAGE', 'odoo:17.0')
DEFAULT_STORAGE_CLASS = os.environ.get('DEFAULT_STORAGE_CLASS', 'standard')
DEFAULT_INGRESS_CLASS = os.environ.get('DEFAULT_INGRESS_CLASS', 'nginx')

# Database connection information from environment variables
DB_HOST = os.environ.get('DB_HOST', 'postgres')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_ADMIN_USER = os.environ.get('DB_ADMIN_USER', 'postgres')
DB_ADMIN_PASSWORD_SECRET = os.environ.get('DB_ADMIN_PASSWORD_SECRET', 'postgres-admin')
DB_ADMIN_PASSWORD_SECRET_KEY = os.environ.get('DB_ADMIN_PASSWORD_SECRET_KEY', 'password')
DB_ADMIN_PASSWORD_SECRET_NAMESPACE = os.environ.get('DB_ADMIN_PASSWORD_SECRET_NAMESPACE', '')

# Initialize Kubernetes API clients
try:
    # Try to load in-cluster config first (when running in a pod)
    from kubernetes import config
    config.load_incluster_config()
    logger.info("Loaded in-cluster Kubernetes configuration")
except Exception:
    # Fall back to local config (for development)
    from kubernetes import config
    config.load_kube_config()
    logger.info("Loaded local Kubernetes configuration")

api_client = k8s.ApiClient()
core_v1 = k8s.CoreV1Api(api_client)
apps_v1 = k8s.AppsV1Api(api_client)
networking_v1 = k8s.NetworkingV1Api(api_client)
custom_objects = k8s.CustomObjectsApi(api_client)

@kopf.on.create(GROUP, VERSION, PLURAL)
def create_odoo_instance(spec, meta, status, **kwargs):
    """
    Handler for OdooInstance creation events
    
    This handler is triggered when a new OdooInstance custom resource is created.
    It creates all the necessary Kubernetes resources for the Odoo instance.
    
    Args:
        spec: The specification of the OdooInstance
        meta: Metadata of the OdooInstance
        status: Current status of the OdooInstance
        **kwargs: Additional arguments passed by Kopf
        
    Returns:
        Dict with status information
    """
    name = meta.get('name')
    namespace = meta.get('namespace')
    logger.info(f"Creating OdooInstance: {name} in namespace: {namespace}")
    
    # Update status to Pending
    patch_status(name, namespace, {
        'phase': 'Pending',
        'message': 'Creating resources',
        'ready': False
    })
    
    # Create required resources
    try:
        # Create filestore PVC
        create_filestore_pvc(name, namespace, spec)
        logger.info(f"Created filestore PVC for {name}")
        
        # Create ConfigMap for custom configuration
        create_config_map(name, namespace, spec)
        logger.info(f"Created ConfigMap for {name}")
        
        # Create Odoo deployment
        create_deployment(name, namespace, spec)
        logger.info(f"Created deployment for {name}")
        
        # Create service
        create_service(name, namespace, spec)
        logger.info(f"Created service for {name}")
        
        # Create ingress if enabled
        url = None
        if spec.get('ingress', {}).get('enabled', True):
            create_ingress(name, namespace, spec)
            logger.info(f"Created ingress for {name}")
            
            # Set URL in status
            if spec.get('ingress', {}).get('hostname'):
                protocol = 'https' if spec.get('ingress', {}).get('tls', True) else 'http'
                url = f"{protocol}://{spec['ingress']['hostname']}"
        
        # Update status to Running
        patch_status(name, namespace, {
            'phase': 'Running',
            'ready': True,
            'url': url,
            'message': 'Odoo instance created successfully'
        })
        
        logger.info(f"Successfully created OdooInstance: {name} in namespace: {namespace}")
        return {
            'status': 'success',
            'message': 'Odoo instance created successfully',
            'url': url
        }
    
    except ApiException as e:
        error_msg = f"Error creating resources: {e}"
        logger.error(error_msg)
        patch_status(name, namespace, {
            'phase': 'Failed',
            'ready': False,
            'message': error_msg
        })
        raise kopf.PermanentError(error_msg)

@kopf.on.update(GROUP, VERSION, PLURAL)
def update_odoo_instance(spec, meta, status, old, diff, **kwargs):
    """
    Handler for OdooInstance update events
    
    This handler is triggered when an OdooInstance custom resource is updated.
    It updates the Kubernetes resources for the Odoo instance based on the changes.
    
    Args:
        spec: The new specification of the OdooInstance
        meta: Metadata of the OdooInstance
        status: Current status of the OdooInstance
        old: The old specification of the OdooInstance
        diff: List of differences between old and new specs
        **kwargs: Additional arguments passed by Kopf
        
    Returns:
        Dict with status information
    """
    name = meta.get('name')
    namespace = meta.get('namespace')
    logger.info(f"Updating OdooInstance: {name} in namespace: {namespace}")
    
    # Update status to reflect we're processing the update
    patch_status(name, namespace, {
        'phase': 'Updating',
        'message': 'Updating resources',
    })
    
    # Log the changes
    for op, path, old_val, new_val in diff:
        path_str = '.'.join(str(p) for p in path)
        logger.info(f"Change detected: {op} {path_str} from {old_val} to {new_val}")
    
    try:
        # Update ConfigMap if needed
        update_config_map(name, namespace, spec)
        
        # Update deployment
        update_deployment(name, namespace, spec)
        
        # Update service if needed
        update_service(name, namespace, spec)
        
        # Update or create ingress if enabled
        url = None
        if spec.get('ingress', {}).get('enabled', True):
            if old.get('ingress', {}).get('enabled', True):
                update_ingress(name, namespace, spec)
            else:
                create_ingress(name, namespace, spec)
                
            # Set URL in status
            if spec.get('ingress', {}).get('hostname'):
                protocol = 'https' if spec.get('ingress', {}).get('tls', True) else 'http'
                url = f"{protocol}://{spec['ingress']['hostname']}"
        elif old.get('ingress', {}).get('enabled', True):
            # Ingress was disabled, delete it
            try:
                networking_v1.delete_namespaced_ingress(
                    name=f"odoo-{name}",
                    namespace=namespace
                )
                logger.info(f"Deleted ingress for {name}")
            except ApiException as e:
                if e.status != 404:  # Not Found is ok
                    raise
        
        # Update status
        patch_status(name, namespace, {
            'phase': 'Running',
            'ready': True,
            'url': url,
            'message': 'Odoo instance updated successfully'
        })
        
        logger.info(f"Successfully updated OdooInstance: {name} in namespace: {namespace}")
        return {
            'status': 'success',
            'message': 'Odoo instance updated successfully'
        }
    
    except ApiException as e:
        error_msg = f"Error updating resources: {e}"
        logger.error(error_msg)
        patch_status(name, namespace, {
            'phase': 'Failed',
            'message': error_msg
        })
        raise kopf.PermanentError(error_msg)

@kopf.on.delete(GROUP, VERSION, PLURAL)
def delete_odoo_instance(spec, meta, status, **kwargs):
    """
    Handler for OdooInstance deletion events
    
    This handler is triggered when an OdooInstance custom resource is deleted.
    It performs any cleanup that might be needed beyond what Kubernetes
    garbage collection handles.
    
    Args:
        spec: The specification of the OdooInstance
        meta: Metadata of the OdooInstance
        status: Current status of the OdooInstance
        **kwargs: Additional arguments passed by Kopf
        
    Returns:
        Dict with status information
    """
    name = meta.get('name')
    namespace = meta.get('namespace')
    logger.info(f"Deleting OdooInstance: {name} in namespace: {namespace}")
    
    # Most resources will be deleted by Kubernetes garbage collection
    # due to the ownerReferences we set on creation
    
    # Clean up database user and database
    try:
        # Get database name and username using helper functions
        db_name = generate_db_name(name, namespace)
        db_user = generate_db_username(name, namespace)
        
        # Import psycopg2 for PostgreSQL connection
        try:
            import psycopg2
            from psycopg2 import sql
        except ImportError:
            logger.error("psycopg2 is not installed. Please install it with 'pip install psycopg2-binary'")
            raise
        
        # Get admin password from secret
        admin_password = None
        try:
            secret_namespace = DB_ADMIN_PASSWORD_SECRET_NAMESPACE or namespace
            secret = core_v1.read_namespaced_secret(
                name=DB_ADMIN_PASSWORD_SECRET,
                namespace=secret_namespace
            )
            import base64
            admin_password = base64.b64decode(secret.data[DB_ADMIN_PASSWORD_SECRET_KEY]).decode('utf-8')
        except ApiException as e:
            logger.error(f"Error reading admin password secret: {e}")
            raise
        
        # Connect to PostgreSQL as admin
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_ADMIN_USER,
            password=admin_password,
            dbname='postgres'  # Connect to default database
        )
        conn.autocommit = True  # Needed for DROP DATABASE
        cursor = conn.cursor()
        
        # Drop database if it exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        if cursor.fetchone() is not None:
            # Terminate all connections to the database
            cursor.execute(
                sql.SQL("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = {}").format(
                    sql.Literal(db_name)
                )
            )
            # Drop the database
            cursor.execute(
                sql.SQL("DROP DATABASE IF EXISTS {}").format(
                    sql.Identifier(db_name)
                )
            )
            logger.info(f"Dropped database {db_name}")
        
        # Drop user if it exists
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (db_user,))
        if cursor.fetchone() is not None:
            cursor.execute(
                sql.SQL("DROP ROLE IF EXISTS {}").format(
                    sql.Identifier(db_user)
                )
            )
            logger.info(f"Dropped database user {db_user}")
        
        # Close connection
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.warning(f"Failed to clean up database user and database: {e}")
        logger.warning("Continuing with deletion, but database resources may not be fully cleaned up")
    
    # Log the deletion
    logger.info(f"OdooInstance {name} in namespace {namespace} has been deleted")
    
    return {
        'status': 'success',
        'message': 'Odoo instance deleted successfully'
    }

def patch_status(name: str, namespace: str, status_patch: Dict[str, Any]) -> None:
    """
    Update the status of an OdooInstance
    
    Args:
        name: Name of the OdooInstance
        namespace: Namespace of the OdooInstance
        status_patch: Status fields to update
    """
    try:
        # Get current status first to avoid overwriting fields
        current = custom_objects.get_namespaced_custom_object(
            group=GROUP,
            version=VERSION,
            namespace=namespace,
            plural=PLURAL,
            name=name
        )
        
        current_status = current.get('status', {})
        
        # Update with new values
        current_status.update(status_patch)
        
        # Patch the status
        custom_objects.patch_namespaced_custom_object_status(
            group=GROUP,
            version=VERSION,
            namespace=namespace,
            plural=PLURAL,
            name=name,
            body={"status": current_status}
        )
    except ApiException as e:
        logger.error(f"Error updating status: {e}")

def create_database_pvc(name: str, namespace: str, spec: Dict[str, Any]) -> None:
    """
    Create a PVC for the Odoo database
    
    Args:
        name: Name of the OdooInstance
        namespace: Namespace of the OdooInstance
        spec: Specification of the OdooInstance
    """
    db_spec = spec.get('database', {})
    storage_size = db_spec.get('storageSize', '10Gi')
    storage_class = db_spec.get('storageClass', DEFAULT_STORAGE_CLASS)
    
    pvc_name = f"odoo-db-{name}"
    
    pvc = {
        'apiVersion': 'v1',
        'kind': 'PersistentVolumeClaim',
        'metadata': {
            'name': pvc_name,
            'namespace': namespace,
            'labels': {
                'app.kubernetes.io/name': 'odoo',
                'app.kubernetes.io/instance': name,
                'app.kubernetes.io/managed-by': 'odoo-operator',
                'app.kubernetes.io/component': 'database'
            },
            'ownerReferences': [{
                'apiVersion': f"{GROUP}/{VERSION}",
                'kind': 'OdooInstance',
                'name': name,
                'uid': custom_objects.get_namespaced_custom_object(
                    group=GROUP,
                    version=VERSION,
                    namespace=namespace,
                    plural=PLURAL,
                    name=name
                )['metadata']['uid'],
                'controller': True,
                'blockOwnerDeletion': True
            }]
        },
        'spec': {
            'accessModes': ['ReadWriteOnce'],
            'resources': {
                'requests': {
                    'storage': storage_size
                }
            },
            'storageClassName': storage_class
        }
    }
    
    try:
        core_v1.create_namespaced_persistent_volume_claim(
            namespace=namespace,
            body=pvc
        )
    except ApiException as e:
        if e.status == 409:  # Conflict means it already exists
            logger.info(f"PVC {pvc_name} already exists, skipping creation")
        else:
            raise

def create_config_map(name: str, namespace: str, spec: Dict[str, Any]) -> None:
    """
    Create a ConfigMap for Odoo configuration
    
    Args:
        name: Name of the OdooInstance
        namespace: Namespace of the OdooInstance
        spec: Specification of the OdooInstance
    """
    config_map_name = f"odoo-config-{name}"
    
    # Create a basic odoo.conf file
    odoo_conf = """
[options]
; This is the password that allows database operations:
admin_passwd = $ODOO_ADMIN_PASSWORD
db_host = $ODOO_DB_HOST
db_port = $ODOO_DB_PORT
db_user = $ODOO_DB_USER
db_password = $ODOO_DB_PASSWORD
addons_path = /mnt/extra-addons
data_dir = /var/lib/odoo
proxy_mode = True
"""
    
    config_map = {
        'apiVersion': 'v1',
        'kind': 'ConfigMap',
        'metadata': {
            'name': config_map_name,
            'namespace': namespace,
            'labels': {
                'app.kubernetes.io/name': 'odoo',
                'app.kubernetes.io/instance': name,
                'app.kubernetes.io/managed-by': 'odoo-operator'
            },
            'ownerReferences': [{
                'apiVersion': f"{GROUP}/{VERSION}",
                'kind': 'OdooInstance',
                'name': name,
                'uid': custom_objects.get_namespaced_custom_object(
                    group=GROUP,
                    version=VERSION,
                    namespace=namespace,
                    plural=PLURAL,
                    name=name
                )['metadata']['uid'],
                'controller': True,
                'blockOwnerDeletion': True
            }]
        },
        'data': {
            'odoo.conf': odoo_conf
        }
    }
    
    try:
        core_v1.create_namespaced_config_map(
            namespace=namespace,
            body=config_map
        )
    except ApiException as e:
        if e.status == 409:  # Conflict means it already exists
            logger.info(f"ConfigMap {config_map_name} already exists, skipping creation")
        else:
            raise

def update_config_map(name: str, namespace: str, spec: Dict[str, Any]) -> None:
    """
    Update the ConfigMap for Odoo configuration
    
    Args:
        name: Name of the OdooInstance
        namespace: Namespace of the OdooInstance
        spec: Specification of the OdooInstance
    """
    config_map_name = f"odoo-config-{name}"
    
    try:
        # Get the current ConfigMap
        current_cm = core_v1.read_namespaced_config_map(
            name=config_map_name,
            namespace=namespace
        )
        
        # Update the ConfigMap data if needed
        # For now, we're just keeping the same configuration
        # In a real operator, you might update this based on changes in the spec
        
        # Apply the update
        core_v1.patch_namespaced_config_map(
            name=config_map_name,
            namespace=namespace,
            body=current_cm
        )
    except ApiException as e:
        if e.status == 404:  # Not Found
            # Create it if it doesn't exist
            create_config_map(name, namespace, spec)
        else:
            raise

def update_service(name: str, namespace: str, spec: Dict[str, Any]) -> None:
    """
    Update the Service for an Odoo instance
    
    Args:
        name: Name of the OdooInstance
        namespace: Namespace of the OdooInstance
        spec: Specification of the OdooInstance
    """
    service_name = f"odoo-{name}"
    
    try:
        # Get the current Service
        current_svc = core_v1.read_namespaced_service(
            name=service_name,
            namespace=namespace
        )
        
        # For now, we don't need to update anything in the service
        # In a real operator, you might update ports or selectors based on changes in the spec
        
        # Apply the update if needed
        # core_v1.patch_namespaced_service(
        #     name=service_name,
        #     namespace=namespace,
        #     body=current_svc
        # )
    except ApiException as e:
        if e.status == 404:  # Not Found
            # Create it if it doesn't exist
            create_service(name, namespace, spec)
        else:
            raise

def create_filestore_pvc(name: str, namespace: str, spec: Dict[str, Any]) -> None:
    """
    Create a PVC for the Odoo filestore
    
    Args:
        name: Name of the OdooInstance
        namespace: Namespace of the OdooInstance
        spec: Specification of the OdooInstance
    """
    filestore_spec = spec.get('filestore', {})
    storage_size = filestore_spec.get('storageSize', '10Gi')
    storage_class = filestore_spec.get('storageClass', DEFAULT_STORAGE_CLASS)
    
    pvc_name = f"odoo-filestore-{name}"
    
    pvc = {
        'apiVersion': 'v1',
        'kind': 'PersistentVolumeClaim',
        'metadata': {
            'name': pvc_name,
            'namespace': namespace,
            'labels': {
                'app.kubernetes.io/name': 'odoo',
                'app.kubernetes.io/instance': name,
                'app.kubernetes.io/managed-by': 'odoo-operator',
                'app.kubernetes.io/component': 'filestore'
            },
            'ownerReferences': [{
                'apiVersion': f"{GROUP}/{VERSION}",
                'kind': 'OdooInstance',
                'name': name,
                'uid': custom_objects.get_namespaced_custom_object(
                    group=GROUP,
                    version=VERSION,
                    namespace=namespace,
                    plural=PLURAL,
                    name=name
                )['metadata']['uid'],
                'controller': True,
                'blockOwnerDeletion': True
            }]
        },
        'spec': {
            'accessModes': ['ReadWriteOnce'],
            'resources': {
                'requests': {
                    'storage': storage_size
                }
            },
            'storageClassName': storage_class
        }
    }
    
    try:
        core_v1.create_namespaced_persistent_volume_claim(
            namespace=namespace,
            body=pvc
        )
    except ApiException as e:
        if e.status == 409:  # Conflict means it already exists
            logger.info(f"PVC {pvc_name} already exists, skipping creation")
        else:
            raise

def create_deployment(name: str, namespace: str, spec: Dict[str, Any]) -> None:
    """
    Create a Deployment for an Odoo instance
    
    Args:
        name: Name of the OdooInstance
        namespace: Namespace of the OdooInstance
        spec: Specification of the OdooInstance
    """
    # Get values from spec or use defaults
    version = spec.get('version')
    image = spec.get('image', f"{DEFAULT_ODOO_IMAGE.split(':')[0]}:{version}")
    replicas = spec.get('replicas', 1)
    resources = spec.get('resources', {})
    
    # Environment variables
    env = []
    
    # Create the database user and database, which will also create the credentials secret
    # This function returns the database credentials that we'll use in the deployment
    try:
        db_user, db_password, db_name = create_database_user(name, namespace)
    except Exception as e:
        logger.warning(f"Failed to create database user and database: {e}")
        logger.warning("Continuing with deployment, but database access may not work correctly")
        # Fall back to generated values if database creation fails
        db_name = generate_db_name(name, namespace)
        db_user = generate_db_username(name, namespace)
        db_password = generate_db_password()
        create_db_credentials_secret(name, namespace, db_user, db_password, db_name)
    
    # Add environment variables for database connection from the secret
    secret_name = f'odoo-db-credentials-{name}'
    env.extend([
        {
            'name': 'ODOO_DB_HOST',
            'valueFrom': {
                'secretKeyRef': {
                    'name': secret_name,
                    'key': 'host'
                }
            }
        },
        {
            'name': 'ODOO_DB_PORT',
            'valueFrom': {
                'secretKeyRef': {
                    'name': secret_name,
                    'key': 'port'
                }
            }
        },
        {
            'name': 'ODOO_DB_USER',
            'valueFrom': {
                'secretKeyRef': {
                    'name': secret_name,
                    'key': 'username'
                }
            }
        },
        {
            'name': 'ODOO_DB_PASSWORD',
            'valueFrom': {
                'secretKeyRef': {
                    'name': secret_name,
                    'key': 'password'
                }
            }
        },
        {
            'name': 'ODOO_DB_NAME',
            'valueFrom': {
                'secretKeyRef': {
                    'name': secret_name,
                    'key': 'database'
                }
            }
        },
        # Use instance-specific admin secret if provided, otherwise use the default
        {
            'name': 'ODOO_ADMIN_PASSWORD',
            'valueFrom': {
                'secretKeyRef': {
                    'name': spec.get('adminSecret', {}).get('name', 'odoo-admin-credentials'),
                    'key': spec.get('adminSecret', {}).get('key', 'admin-password')
                }
            }
        }
    ])
    
    # Add custom environment variables from spec
    if 'env' in spec and spec['env']:
        for env_var in spec['env']:
            # Check if this env var is already in the list
            existing = next((e for e in env if e['name'] == env_var['name']), None)
            if existing:
                # Replace existing env var
                env.remove(existing)
            env.append(env_var)
    
    # Create volumes and volume mounts
    volumes = [
        {
            'name': 'odoo-config',
            'configMap': {
                'name': f"odoo-config-{name}"
            }
        },
        {
            'name': 'odoo-filestore',
            'persistentVolumeClaim': {
                'claimName': f"odoo-filestore-{name}"
            }
        }
    ]
    
    volume_mounts = [
        {
            'name': 'odoo-config',
            'mountPath': '/etc/odoo',
            'readOnly': True
        },
        {
            'name': 'odoo-filestore',
            'mountPath': '/var/lib/odoo',
            'subPath': 'filestore'
        }
    ]
    
    # Database connection is now handled via environment variables
    
    # Add volumes for addons if specified
    if spec.get('addons'):
        volumes.append({
            'name': 'odoo-addons',
            'emptyDir': {}
        })
        volume_mounts.append({
            'name': 'odoo-addons',
            'mountPath': '/mnt/extra-addons'
        })
    
    # Create the deployment
    deployment = {
        'apiVersion': 'apps/v1',
        'kind': 'Deployment',
        'metadata': {
            'name': f"odoo-{name}",
            'namespace': namespace,
            'labels': {
                'app.kubernetes.io/name': 'odoo',
                'app.kubernetes.io/instance': name,
                'app.kubernetes.io/version': version,
                'app.kubernetes.io/managed-by': 'odoo-operator'
            },
            'ownerReferences': [{
                'apiVersion': f"{GROUP}/{VERSION}",
                'kind': 'OdooInstance',
                'name': name,
                'uid': custom_objects.get_namespaced_custom_object(
                    group=GROUP,
                    version=VERSION,
                    namespace=namespace,
                    plural=PLURAL,
                    name=name
                )['metadata']['uid'],
                'controller': True,
                'blockOwnerDeletion': True
            }]
        },
        'spec': {
            'replicas': replicas,
            'selector': {
                'matchLabels': {
                    'app.kubernetes.io/name': 'odoo',
                    'app.kubernetes.io/instance': name
                }
            },
            'template': {
                'metadata': {
                    'labels': {
                        'app.kubernetes.io/name': 'odoo',
                        'app.kubernetes.io/instance': name,
                        'app.kubernetes.io/version': version
                    }
                },
                'spec': {
                    'containers': [
                        {
                            'name': 'odoo',
                            'image': image,
                            'ports': [
                                {
                                    'name': 'http',
                                    'containerPort': 8069,
                                    'protocol': 'TCP'
                                },
                                {
                                    'name': 'longpolling',
                                    'containerPort': 8072,
                                    'protocol': 'TCP'
                                }
                            ],
                            'env': env,
                            'volumeMounts': volume_mounts,
                            'resources': resources,
                            'livenessProbe': {
                                'httpGet': {
                                    'path': '/web/health',
                                    'port': 'http'
                                },
                                'initialDelaySeconds': 60,
                                'periodSeconds': 10,
                                'timeoutSeconds': 5,
                                'failureThreshold': 6
                            },
                            'readinessProbe': {
                                'httpGet': {
                                    'path': '/web/health',
                                    'port': 'http'
                                },
                                'initialDelaySeconds': 30,
                                'periodSeconds': 10,
                                'timeoutSeconds': 5,
                                'successThreshold': 1,
                                'failureThreshold': 6
                            }
                        }
                    ],
                    'volumes': volumes
                }
            }
        }
    }
    
    # Add init container for addons if needed
    if spec.get('addons'):
        init_containers = []
        
        # Create an init container for each addon repo
        for i, addon in enumerate(spec.get('addons', [])):
            repo = addon.get('repo')
            branch = addon.get('branch', 'main')
            path = addon.get('path', '')
            
            # Create init container for this addon
            init_container = {
                'name': f"clone-addons-{i}",
                'image': 'alpine/git:latest',
                'command': ['sh', '-c'],
                'args': [
                    f"git clone --depth 1 --branch {branch} {repo} /tmp/addons && "
                    f"mkdir -p /mnt/extra-addons/{i} && "
                    f"cp -r /tmp/addons/{path}/* /mnt/extra-addons/{i}/"
                ],
                'volumeMounts': [
                    {
                        'name': 'odoo-addons',
                        'mountPath': '/mnt/extra-addons'
                    }
                ]
            }
            
            init_containers.append(init_container)
        
        # Add init containers to deployment
        deployment['spec']['template']['spec']['initContainers'] = init_containers
    
    # Create the deployment
    try:
        apps_v1.create_namespaced_deployment(
            namespace=namespace,
            body=deployment
        )
    except ApiException as e:
        if e.status == 409:  # Conflict means it already exists
            logger.info(f"Deployment odoo-{name} already exists, skipping creation")
        else:
            raise

def create_service(name: str, namespace: str, spec: Dict[str, Any]) -> None:
    """
    Create a Service for an Odoo instance
    
    Args:
        name: Name of the OdooInstance
        namespace: Namespace of the OdooInstance
        spec: Specification of the OdooInstance
    """
    service = {
        'apiVersion': 'v1',
        'kind': 'Service',
        'metadata': {
            'name': f"odoo-{name}",
            'namespace': namespace,
            'labels': {
                'app.kubernetes.io/name': 'odoo',
                'app.kubernetes.io/instance': name,
                'app.kubernetes.io/managed-by': 'odoo-operator'
            },
            'ownerReferences': [{
                'apiVersion': f"{GROUP}/{VERSION}",
                'kind': 'OdooInstance',
                'name': name,
                'uid': custom_objects.get_namespaced_custom_object(
                    group=GROUP,
                    version=VERSION,
                    namespace=namespace,
                    plural=PLURAL,
                    name=name
                )['metadata']['uid'],
                'controller': True,
                'blockOwnerDeletion': True
            }]
        },
        'spec': {
            'ports': [
                {
                    'name': 'http',
                    'port': 80,
                    'targetPort': 8069,
                    'protocol': 'TCP'
                },
                {
                    'name': 'longpolling',
                    'port': 8072,
                    'targetPort': 8072,
                    'protocol': 'TCP'
                }
            ],
            'selector': {
                'app.kubernetes.io/name': 'odoo',
                'app.kubernetes.io/instance': name
            },
            'type': 'ClusterIP'
        }
    }
    
    try:
        core_v1.create_namespaced_service(
            namespace=namespace,
            body=service
        )
    except ApiException as e:
        if e.status == 409:  # Conflict means it already exists
            logger.info(f"Service odoo-{name} already exists, skipping creation")
        else:
            raise

def create_ingress(name: str, namespace: str, spec: Dict[str, Any]) -> None:
    """
    Create an Ingress for an Odoo instance
    
    Args:
        name: Name of the OdooInstance
        namespace: Namespace of the OdooInstance
        spec: Specification of the OdooInstance
    """
    ingress_spec = spec.get('ingress', {})
    hostname = ingress_spec.get('hostname')
    class_name = ingress_spec.get('className', DEFAULT_INGRESS_CLASS)
    tls_enabled = ingress_spec.get('tls', True)
    tls_secret = ingress_spec.get('tlsSecret')
    annotations = ingress_spec.get('annotations', {})
    
    # Skip if hostname is not provided
    if not hostname:
        logger.warning(f"Ingress hostname not specified for {name}, skipping ingress creation")
        return
    
    # Create ingress object
    ingress = {
        'apiVersion': 'networking.k8s.io/v1',
        'kind': 'Ingress',
        'metadata': {
            'name': f"odoo-{name}",
            'namespace': namespace,
            'labels': {
                'app.kubernetes.io/name': 'odoo',
                'app.kubernetes.io/instance': name,
                'app.kubernetes.io/managed-by': 'odoo-operator'
            },
            'annotations': annotations,
            'ownerReferences': [{
                'apiVersion': f"{GROUP}/{VERSION}",
                'kind': 'OdooInstance',
                'name': name,
                'uid': custom_objects.get_namespaced_custom_object(
                    group=GROUP,
                    version=VERSION,
                    namespace=namespace,
                    plural=PLURAL,
                    name=name
                )['metadata']['uid'],
                'controller': True,
                'blockOwnerDeletion': True
            }]
        },
        'spec': {
            'ingressClassName': class_name,
            'rules': [
                {
                    'host': hostname,
                    'http': {
                        'paths': [
                            {
                                'path': '/',
                                'pathType': 'Prefix',
                                'backend': {
                                    'service': {
                                        'name': f"odoo-{name}",
                                        'port': {
                                            'name': 'http'
                                        }
                                    }
                                }
                            }
                        ]
                    }
                }
            ]
        }
    }
    
    # Add TLS configuration if enabled
    if tls_enabled:
        tls_config = {
            'hosts': [hostname]
        }
        
        # Add secretName if provided
        if tls_secret:
            tls_config['secretName'] = tls_secret
        else:
            # Use a default name based on the hostname
            tls_config['secretName'] = f"odoo-{name}-tls"
        
        ingress['spec']['tls'] = [tls_config]
    
    try:
        networking_v1.create_namespaced_ingress(
            namespace=namespace,
            body=ingress
        )
    except ApiException as e:
        if e.status == 409:  # Conflict means it already exists
            logger.info(f"Ingress odoo-{name} already exists, skipping creation")
        else:
            raise
        logger.info(f"Created PVC: {pvc_name} in namespace: {namespace}")
    except ApiException as e:
        if e.status == 409:  # Already exists
            logger.info(f"PVC {pvc_name} already exists in namespace: {namespace}")
        else:
            raise

def create_deployment(name, namespace, spec):
    """
    Create a deployment for Odoo
    """
    image = spec.get('image', f"{DEFAULT_ODOO_IMAGE}")
    if not image:
        image = f"odoo:{spec.get('version', '17.0')}"
    
    replicas = spec.get('replicas', 1)
    
    resources = spec.get('resources', {
        'limits': {
            'cpu': '2',
            'memory': '4Gi'
        },
        'requests': {
            'cpu': '500m',
            'memory': '1Gi'
        }
    })
    
    env = spec.get('env', [])
    
    deployment = {
        'apiVersion': 'apps/v1',
        'kind': 'Deployment',
        'metadata': {
            'name': name,
            'namespace': namespace,
            'labels': {
                'app.kubernetes.io/name': 'odoo',
                'app.kubernetes.io/instance': name,
                'app.kubernetes.io/managed-by': 'odoo-operator'
            },
            'ownerReferences': [{
                'apiVersion': f"{GROUP}/{VERSION}",
                'kind': 'OdooInstance',
                'name': name,
                'uid': custom_objects.get_namespaced_custom_object(
                    group=GROUP,
                    version=VERSION,
                    namespace=namespace,
                    plural=PLURAL,
                    name=name
                )['metadata']['uid'],
                'controller': True,
                'blockOwnerDeletion': True
            }]
        },
        'spec': {
            'replicas': replicas,
            'selector': {
                'matchLabels': {
                    'app.kubernetes.io/name': 'odoo',
                    'app.kubernetes.io/instance': name
                }
            },
            'template': {
                'metadata': {
                    'labels': {
                        'app.kubernetes.io/name': 'odoo',
                        'app.kubernetes.io/instance': name
                    }
                },
                'spec': {
                    'containers': [{
                        'name': 'odoo',
                        'image': image,
                        'ports': [
                            {
                                'name': 'http',
                                'containerPort': 8069,
                                'protocol': 'TCP'
                            },
                            {
                                'name': 'longpolling',
                                'containerPort': 8072,
                                'protocol': 'TCP'
                            }
                        ],
                        'volumeMounts': [
                            {
                                'name': 'filestore',
                                'mountPath': '/var/lib/odoo'
                            }
                        ],
                        'resources': resources,
                        'env': env
                    }],
                    'volumes': [
                        {
                            'name': 'filestore',
                            'persistentVolumeClaim': {
                                'claimName': f"{name}-filestore"
                            }
                        }
                    ]
                }
            }
        }
    }
    
    # Add addon volumes if specified
    addons = spec.get('addons', [])
    if addons:
        # Create init container to clone repos
        init_containers = []
        addon_volume_mounts = []
        
        for i, addon in enumerate(addons):
            repo = addon.get('repo')
            branch = addon.get('branch', 'main')
            path = addon.get('path', '')
            
            volume_name = f"addon-{i}"
            mount_path = f"/mnt/addons/{i}"
            
            # Add volume
            deployment['spec']['template']['spec']['volumes'].append({
                'name': volume_name,
                'emptyDir': {}
            })
            
            # Add init container to clone repo
            init_containers.append({
                'name': f"clone-{i}",
                'image': 'alpine/git',
                'command': ['git', 'clone', '--depth', '1', '--branch', branch, repo, mount_path],
                'volumeMounts': [{
                    'name': volume_name,
                    'mountPath': mount_path
                }]
            })
            
            # Add volume mount to Odoo container
            target_path = f"/mnt/extra-addons/{i}"
            if path:
                target_path = f"{target_path}/{path}"
            
            addon_volume_mounts.append({
                'name': volume_name,
                'mountPath': target_path,
                'subPath': path
            })
        
        # Add init containers
        deployment['spec']['template']['spec']['initContainers'] = init_containers
        
        # Add addon volume mounts to Odoo container
        deployment['spec']['template']['spec']['containers'][0]['volumeMounts'].extend(addon_volume_mounts)
    
    try:
        apps_v1.create_namespaced_deployment(
            namespace=namespace,
            body=deployment
        )
        logger.info(f"Created Deployment: {name} in namespace: {namespace}")
    except ApiException as e:
        if e.status == 409:  # Already exists
            logger.info(f"Deployment {name} already exists in namespace: {namespace}")
        else:
            raise

def update_deployment(name, namespace, spec):
    """
    Update an existing Odoo deployment
    """
    try:
        # Get current deployment
        current_deployment = apps_v1.read_namespaced_deployment(
            name=name,
            namespace=namespace
        )
        
        # Update deployment with new spec
        image = spec.get('image', f"{DEFAULT_ODOO_IMAGE}")
        if not image:
            image = f"odoo:{spec.get('version', '17.0')}"
        
        replicas = spec.get('replicas', 1)
        resources = spec.get('resources', {})
        env = spec.get('env', [])
        
        current_deployment.spec.replicas = replicas
        current_deployment.spec.template.spec.containers[0].image = image
        
        if resources:
            current_deployment.spec.template.spec.containers[0].resources = resources
        
        if env:
            current_deployment.spec.template.spec.containers[0].env = env
        
        # Update the deployment
        apps_v1.patch_namespaced_deployment(
            name=name,
            namespace=namespace,
            body=current_deployment
        )
        logger.info(f"Updated Deployment: {name} in namespace: {namespace}")
    
    except ApiException as e:
        if e.status == 404:  # Not found
            # Create it
            create_deployment(name, namespace, spec)
        else:
            raise

def create_service(name, namespace, spec):
    """
    Create a service for Odoo
    """
    service = {
        'apiVersion': 'v1',
        'kind': 'Service',
        'metadata': {
            'name': name,
            'namespace': namespace,
            'labels': {
                'app.kubernetes.io/name': 'odoo',
                'app.kubernetes.io/instance': name,
                'app.kubernetes.io/managed-by': 'odoo-operator'
            },
            'ownerReferences': [{
                'apiVersion': f"{GROUP}/{VERSION}",
                'kind': 'OdooInstance',
                'name': name,
                'uid': custom_objects.get_namespaced_custom_object(
                    group=GROUP,
                    version=VERSION,
                    namespace=namespace,
                    plural=PLURAL,
                    name=name
                )['metadata']['uid'],
                'controller': True,
                'blockOwnerDeletion': True
            }]
        },
        'spec': {
            'selector': {
                'app.kubernetes.io/name': 'odoo',
                'app.kubernetes.io/instance': name
            },
            'ports': [
                {
                    'name': 'http',
                    'port': 80,
                    'targetPort': 'http',
                    'protocol': 'TCP'
                },
                {
                    'name': 'longpolling',
                    'port': 8072,
                    'targetPort': 'longpolling',
                    'protocol': 'TCP'
                }
            ]
        }
    }
    
    try:
        core_v1.create_namespaced_service(
            namespace=namespace,
            body=service
        )
        logger.info(f"Created Service: {name} in namespace: {namespace}")
    except ApiException as e:
        if e.status == 409:  # Already exists
            logger.info(f"Service {name} already exists in namespace: {namespace}")
        else:
            raise

def create_ingress(name, namespace, spec):
    """
    Create an ingress for Odoo
    """
    ingress_spec = spec.get('ingress', {})
    hostname = ingress_spec.get('hostname')
    ingress_class = ingress_spec.get('className', DEFAULT_INGRESS_CLASS)
    annotations = ingress_spec.get('annotations', {})
    tls = ingress_spec.get('tls', True)
    tls_secret = ingress_spec.get('tlsSecret', f"{name}-tls")
    
    ingress = {
        'apiVersion': 'networking.k8s.io/v1',
        'kind': 'Ingress',
        'metadata': {
            'name': name,
            'namespace': namespace,
            'labels': {
                'app.kubernetes.io/name': 'odoo',
                'app.kubernetes.io/instance': name,
                'app.kubernetes.io/managed-by': 'odoo-operator'
            },
            'annotations': annotations,
            'ownerReferences': [{
                'apiVersion': f"{GROUP}/{VERSION}",
                'kind': 'OdooInstance',
                'name': name,
                'uid': custom_objects.get_namespaced_custom_object(
                    group=GROUP,
                    version=VERSION,
                    namespace=namespace,
                    plural=PLURAL,
                    name=name
                )['metadata']['uid'],
                'controller': True,
                'blockOwnerDeletion': True
            }]
        },
        'spec': {
            'ingressClassName': ingress_class,
            'rules': [
                {
                    'host': hostname,
                    'http': {
                        'paths': [
                            {
                                'path': '/',
                                'pathType': 'Prefix',
                                'backend': {
                                    'service': {
                                        'name': name,
                                        'port': {
                                            'name': 'http'
                                        }
                                    }
                                }
                            }
                        ]
                    }
                }
            ]
        }
    }
    
    # Add TLS if enabled
    if tls:
        ingress['spec']['tls'] = [
            {
                'hosts': [hostname],
                'secretName': tls_secret
            }
        ]
    
    try:
        networking_v1.create_namespaced_ingress(
            namespace=namespace,
            body=ingress
        )
        logger.info(f"Created Ingress: {name} in namespace: {namespace}")
    except ApiException as e:
        if e.status == 409:  # Already exists
            logger.info(f"Ingress {name} already exists in namespace: {namespace}")
        else:
            raise

def update_ingress(name, namespace, spec):
    """
    Update an existing Odoo ingress
    """
    try:
        # Get current ingress
        current_ingress = networking_v1.read_namespaced_ingress(
            name=name,
            namespace=namespace
        )
        
        # Update ingress with new spec
        ingress_spec = spec.get('ingress', {})
        hostname = ingress_spec.get('hostname')
        ingress_class = ingress_spec.get('className', DEFAULT_INGRESS_CLASS)
        annotations = ingress_spec.get('annotations', {})
        tls = ingress_spec.get('tls', True)
        tls_secret = ingress_spec.get('tlsSecret', f"{name}-tls")
        
        current_ingress.spec.ingress_class_name = ingress_class
        
        if hostname:
            current_ingress.spec.rules[0].host = hostname
        
        if annotations:
            current_ingress.metadata.annotations = annotations
        
        if tls:
            current_ingress.spec.tls = [
                {
                    'hosts': [hostname],
                    'secretName': tls_secret
                }
            ]
        else:
            current_ingress.spec.tls = []
        
        # Update the ingress
        networking_v1.patch_namespaced_ingress(
            name=name,
            namespace=namespace,
            body=current_ingress
        )
        logger.info(f"Updated Ingress: {name} in namespace: {namespace}")
    
    except ApiException as e:
        if e.status == 404:  # Not found
            # Create it
            create_ingress(name, namespace, spec)
        else:
            raise

def create_database_user(name: str, namespace: str, db_password: str = None) -> None:
    """
    Create a database user and database for an Odoo instance
    
    This function creates a PostgreSQL user and database for an Odoo instance.
    It uses the admin credentials from the environment variables to connect to the database.
    Database name and username are generated from the instance name using helper functions.
    
    Args:
        name: Name of the OdooInstance
        namespace: Namespace of the OdooInstance
        db_password: Database password for the new user (if None, a random password will be generated)
    """
    # Generate database name and username using helper functions
    db_name = generate_db_name(name, namespace)
    db_user = generate_db_username(name, namespace)
    
    # Generate a random password if not provided
    if db_password is None:
        db_password = generate_db_password()
    
    # Import psycopg2 for PostgreSQL connection
    try:
        import psycopg2
        from psycopg2 import sql
    except ImportError:
        logger.error("psycopg2 is not installed. Please install it with 'pip install psycopg2-binary'")
        raise
    
    # Get admin password from secret
    admin_password = None
    try:
        secret_namespace = DB_ADMIN_PASSWORD_SECRET_NAMESPACE or namespace
        secret = core_v1.read_namespaced_secret(
            name=DB_ADMIN_PASSWORD_SECRET,
            namespace=secret_namespace
        )
        import base64
        admin_password = base64.b64decode(secret.data[DB_ADMIN_PASSWORD_SECRET_KEY]).decode('utf-8')
    except ApiException as e:
        logger.error(f"Error reading admin password secret: {e}")
        raise
    
    # Connect to PostgreSQL as admin
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_ADMIN_USER,
            password=admin_password,
            dbname='postgres'  # Connect to default database
        )
        conn.autocommit = True  # Needed for CREATE DATABASE
        cursor = conn.cursor()
        
        # Check if user already exists
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (db_user,))
        if cursor.fetchone() is None:
            # Create user
            cursor.execute(
                sql.SQL("CREATE USER {} WITH PASSWORD {}").format(
                    sql.Identifier(db_user),
                    sql.Literal(db_password)
                )
            )
            logger.info(f"Created database user {db_user}")
        else:
            # Update user password
            cursor.execute(
                sql.SQL("ALTER USER {} WITH PASSWORD {}").format(
                    sql.Identifier(db_user),
                    sql.Literal(db_password)
                )
            )
            logger.info(f"Updated password for database user {db_user}")
        
        # Check if database already exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        if cursor.fetchone() is None:
            # Create database
            cursor.execute(
                sql.SQL("CREATE DATABASE {} OWNER {}").format(
                    sql.Identifier(db_name),
                    sql.Identifier(db_user)
                )
            )
            logger.info(f"Created database {db_name} owned by {db_user}")
        else:
            # Update database owner
            cursor.execute(
                sql.SQL("ALTER DATABASE {} OWNER TO {}").format(
                    sql.Identifier(db_name),
                    sql.Identifier(db_user)
                )
            )
            logger.info(f"Updated owner of database {db_name} to {db_user}")
        
        # Close connection
        cursor.close()
        conn.close()
        
        # Create or update the database credentials secret with all connection information
        create_db_credentials_secret(name, namespace, db_user, db_password, db_name)
        
        # Return the database credentials for use by the caller
        return db_user, db_password, db_name
        
    except Exception as e:
        logger.error(f"Error creating database user or database: {e}")
        raise

def create_db_credentials_secret(name: str, namespace: str, db_user: str, db_password: str, db_name: str = None) -> None:
    """
    Create a Secret for database credentials
    
    Args:
        name: Name of the OdooInstance
        namespace: Namespace of the OdooInstance
        db_user: Database username
        db_password: Database password
        db_name: Database name (optional)
    """
    secret_name = f'odoo-db-credentials-{name}'
    
    import base64
    secret = {
        'apiVersion': 'v1',
        'kind': 'Secret',
        'metadata': {
            'name': secret_name,
            'namespace': namespace,
            'labels': {
                'app.kubernetes.io/name': 'odoo',
                'app.kubernetes.io/instance': name,
                'app.kubernetes.io/managed-by': 'odoo-operator'
            },
            'ownerReferences': [{
                'apiVersion': f"{GROUP}/{VERSION}",
                'kind': 'OdooInstance',
                'name': name,
                'uid': custom_objects.get_namespaced_custom_object(
                    group=GROUP,
                    version=VERSION,
                    namespace=namespace,
                    plural=PLURAL,
                    name=name
                )['metadata']['uid'],
                'controller': True,
                'blockOwnerDeletion': True
            }]
        },
        'type': 'Opaque',
        'data': {
            'host': base64.b64encode(DB_HOST.encode()).decode(),
            'port': base64.b64encode(DB_PORT.encode()).decode(),
            'username': base64.b64encode(db_user.encode()).decode(),
            'password': base64.b64encode(db_password.encode()).decode(),
            # Include database name if provided
            **(({'database': base64.b64encode(db_name.encode()).decode()} if db_name else {}))
        }
    }
    
    try:
        core_v1.create_namespaced_secret(
            namespace=namespace,
            body=secret
        )
        logger.info(f"Created Secret {secret_name} for database credentials")
    except ApiException as e:
        if e.status == 409:  # Conflict means it already exists
            logger.info(f"Secret {secret_name} already exists, skipping creation")
        else:
            raise

def generate_db_name(instance_name: str, namespace: str) -> str:
    """
    Generate a database name for an Odoo instance
    
    Args:
        instance_name: Name of the OdooInstance
        namespace: Namespace of the OdooInstance
        
    Returns:
        Database name
    """
    # PostgreSQL database names are limited to 63 characters
    # Include namespace to ensure uniqueness across namespaces
    return f'odoo_{namespace}_{instance_name}'[:63]

def generate_db_username(instance_name: str, namespace: str) -> str:
    """
    Generate a database username for an Odoo instance
    
    Args:
        instance_name: Name of the OdooInstance
        namespace: Namespace of the OdooInstance
        
    Returns:
        Database username
    """
    # PostgreSQL usernames are limited to 63 characters
    # Include namespace to ensure uniqueness across namespaces
    return f'odoo_user_{namespace}_{instance_name}'[:63]

def generate_db_password() -> str:
    """
    Generate a random password for a database user
    
    Returns:
        Random password
    """
    import random
    import string
    # Generate a 16-character random password with letters and digits
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))

# Initialize Flask app for webhook endpoints
app = Flask(__name__)

# Webhook handlers
def validate_odoo_instance(instance: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate an OdooInstance resource
    
    Args:
        instance: The OdooInstance resource to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    spec = instance.get('spec', {})
    
    # Validate required fields
    if not spec.get('version'):
        return False, "'version' is required in the OdooInstance spec"
    
    # Validate image if specified
    if 'image' in spec and not spec['image']:
        return False, "'image' cannot be empty if specified"
    
    # Validate replicas
    if 'replicas' in spec:
        try:
            replicas = int(spec['replicas'])
            if replicas < 1:
                return False, "'replicas' must be at least 1"
        except (ValueError, TypeError):
            return False, "'replicas' must be a valid integer"
    
    # Validate resources if specified
    if 'resources' in spec:
        resources = spec['resources']
        if 'limits' in resources:
            limits = resources['limits']
            if 'memory' in limits and not re.match(r'^\d+[KMGTPEkmgtpe]i?$', limits['memory']):
                return False, "Invalid memory limit format"
            if 'cpu' in limits and not re.match(r'^\d+m?$', limits['cpu']):
                return False, "Invalid CPU limit format"
    
    return True, None

def mutate_odoo_instance(instance: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mutate an OdooInstance resource by setting default values
    
    Args:
        instance: The OdooInstance resource to mutate
        
    Returns:
        The mutated OdooInstance resource
    """
    if 'spec' not in instance:
        instance['spec'] = {}
    
    spec = instance['spec']
    
    # Set default values
    if 'replicas' not in spec:
        spec['replicas'] = 1
    
    if 'ingress' not in spec:
        spec['ingress'] = {}
    
    ingress = spec['ingress']
    if 'tls' not in ingress:
        ingress['tls'] = True
    
    if 'resources' not in spec:
        spec['resources'] = {
            'limits': {
                'memory': '512Mi',
                'cpu': '500m'
            },
            'requests': {
                'memory': '256Mi',
                'cpu': '250m'
            }
        }
    
    return instance

@app.route('/validate-odoo-bemade-org-v1-odooinstance', methods=['POST'])
def validate_odoo_instance_webhook():
    """
    Webhook endpoint for validating OdooInstance resources
    """
    request_info = request.json
    
    if not request_info:
        return jsonify({
            'apiVersion': 'admission.k8s.io/v1',
            'kind': 'AdmissionReview',
            'response': {
                'uid': '',
                'allowed': False,
                'status': {
                    'code': HTTPStatus.BAD_REQUEST,
                    'message': 'No request information provided'
                }
            }
        }), HTTPStatus.BAD_REQUEST
    
    request_data = request_info.get('request', {})
    uid = request_data.get('uid', '')
    
    try:
        # Extract the OdooInstance from the request
        instance = request_data.get('object', {})
        
        # Validate the OdooInstance
        is_valid, error_message = validate_odoo_instance(instance)
        
        if is_valid:
            response = {
                'apiVersion': 'admission.k8s.io/v1',
                'kind': 'AdmissionReview',
                'response': {
                    'uid': uid,
                    'allowed': True
                }
            }
        else:
            response = {
                'apiVersion': 'admission.k8s.io/v1',
                'kind': 'AdmissionReview',
                'response': {
                    'uid': uid,
                    'allowed': False,
                    'status': {
                        'message': error_message
                    }
                }
            }
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error validating OdooInstance: {e}")
        return jsonify({
            'apiVersion': 'admission.k8s.io/v1',
            'kind': 'AdmissionReview',
            'response': {
                'uid': uid,
                'allowed': False,
                'status': {
                    'message': f"Error validating OdooInstance: {str(e)}"
                }
            }
        })

@app.route('/mutate-odoo-bemade-org-v1-odooinstance', methods=['POST'])
def mutate_odoo_instance_webhook():
    """
    Webhook endpoint for mutating OdooInstance resources
    """
    request_info = request.json
    
    if not request_info:
        return jsonify({
            'apiVersion': 'admission.k8s.io/v1',
            'kind': 'AdmissionReview',
            'response': {
                'uid': '',
                'allowed': False,
                'status': {
                    'code': HTTPStatus.BAD_REQUEST,
                    'message': 'No request information provided'
                }
            }
        }), HTTPStatus.BAD_REQUEST
    
    request_data = request_info.get('request', {})
    uid = request_data.get('uid', '')
    
    try:
        # Extract the OdooInstance from the request
        instance = request_data.get('object', {})
        
        # Mutate the OdooInstance
        mutated_instance = mutate_odoo_instance(instance)
        
        # Create a JSON patch for the changes
        import jsonpatch
        patch = jsonpatch.make_patch(instance, mutated_instance)
        patch_list = patch.patch
        
        # Convert the patch to the format expected by Kubernetes
        k8s_patch = []
        for p in patch_list:
            k8s_patch.append({
                'op': p['op'],
                'path': p['path'],
                'value': p.get('value', None)
            })
        
        response = {
            'apiVersion': 'admission.k8s.io/v1',
            'kind': 'AdmissionReview',
            'response': {
                'uid': uid,
                'allowed': True,
                'patchType': 'JSONPatch',
                'patch': base64.b64encode(json.dumps(k8s_patch).encode()).decode()
            }
        }
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error mutating OdooInstance: {e}")
        return jsonify({
            'apiVersion': 'admission.k8s.io/v1',
            'kind': 'AdmissionReview',
            'response': {
                'uid': uid,
                'allowed': False,
                'status': {
                    'message': f"Error mutating OdooInstance: {str(e)}"
                }
            }
        })

if __name__ == "__main__":
    # Start the Flask app in a separate thread
    import threading
    import ssl
    
    # Configure SSL for the webhook server
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    cert_path = os.environ.get('WEBHOOK_CERT_PATH', '/tmp/k8s-webhook-server/serving-certs/tls.crt')
    key_path = os.environ.get('WEBHOOK_KEY_PATH', '/tmp/k8s-webhook-server/serving-certs/tls.key')
    
    if os.path.exists(cert_path) and os.path.exists(key_path):
        ssl_context.load_cert_chain(cert_path, key_path)
        
        def run_flask_app():
            app.run(
                host='0.0.0.0',
                port=443,
                ssl_context=ssl_context,
                debug=False,
                use_reloader=False
            )
        
        # Start Flask app in a separate thread
        flask_thread = threading.Thread(target=run_flask_app)
        flask_thread.daemon = True
        flask_thread.start()
        logger.info("Webhook server started on port 443")
    else:
        logger.warning(f"Webhook certificates not found at {cert_path} and {key_path}. Webhooks will not be available.")
    
    # Start the Kopf operator
    kopf.run()
