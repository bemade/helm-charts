"""
Type definitions for Odoo operator custom resources.
"""
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field


class ResourceRequirements(BaseModel):
    """Kubernetes resource requirements"""
    limits: Optional[Dict[str, str]] = None
    requests: Optional[Dict[str, str]] = None


class EnvVar(BaseModel):
    """Environment variable"""
    name: str
    value: Optional[str] = None
    valueFrom: Optional[Dict] = None


class DatabaseSpec(BaseModel):
    """Database configuration"""
    storageSize: Optional[str] = None
    storageClass: Optional[str] = None


class FilestoreSpec(BaseModel):
    """Filestore configuration"""
    storageSize: Optional[str] = None
    storageClass: Optional[str] = None
    snapshotClass: Optional[str] = None


class AddonRepo(BaseModel):
    """Addon repository configuration"""
    repo: str
    branch: Optional[str] = "main"
    path: Optional[str] = None


class IngressSpec(BaseModel):
    """Ingress configuration"""
    enabled: bool = True
    hostname: Optional[str] = None
    className: Optional[str] = None
    annotations: Optional[Dict[str, str]] = None
    tls: bool = True
    tlsSecret: Optional[str] = None


class OdooInstanceSpec(BaseModel):
    """Specification for an Odoo instance"""
    version: str
    image: Optional[str] = None
    replicas: int = 1
    resources: Optional[ResourceRequirements] = None
    database: Optional[DatabaseSpec] = None
    filestore: Optional[FilestoreSpec] = None
    addons: Optional[List[AddonRepo]] = None
    ingress: Optional[IngressSpec] = None
    env: Optional[List[EnvVar]] = None


class OdooInstanceStatus(BaseModel):
    """Status of an Odoo instance"""
    phase: Optional[str] = None
    ready: Optional[bool] = None
    url: Optional[str] = None
    message: Optional[str] = None


class OdooInstance(BaseModel):
    """Odoo instance custom resource"""
    apiVersion: str = "odoo.bemade.org/v1"
    kind: str = "OdooInstance"
    metadata: Dict
    spec: OdooInstanceSpec
    status: Optional[OdooInstanceStatus] = None
