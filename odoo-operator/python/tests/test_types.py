"""
Tests for the Odoo operator types.
"""
import pytest
from ..types import OdooInstance, OdooInstanceSpec, ResourceRequirements, IngressSpec


def test_odoo_instance_minimal():
    """Test creating a minimal OdooInstance"""
    instance = OdooInstance(
        metadata={"name": "test", "namespace": "default"},
        spec=OdooInstanceSpec(version="17.0")
    )
    
    assert instance.apiVersion == "odoo.bemade.org/v1"
    assert instance.kind == "OdooInstance"
    assert instance.metadata["name"] == "test"
    assert instance.spec.version == "17.0"
    assert instance.spec.replicas == 1  # Default value


def test_odoo_instance_full():
    """Test creating a full OdooInstance with all fields"""
    instance = OdooInstance(
        metadata={"name": "test", "namespace": "default"},
        spec=OdooInstanceSpec(
            version="17.0",
            image="custom/odoo:17.0",
            replicas=2,
            resources=ResourceRequirements(
                limits={"cpu": "2", "memory": "4Gi"},
                requests={"cpu": "500m", "memory": "1Gi"}
            ),
            database={
                "storageSize": "10Gi",
                "storageClass": "standard"
            },
            filestore={
                "storageSize": "20Gi",
                "storageClass": "standard",
                "snapshotClass": "csi-hostpath-snapclass"
            },
            addons=[
                {"repo": "https://github.com/OCA/web", "branch": "17.0"},
                {"repo": "https://github.com/bemade/custom-addons", "branch": "main"}
            ],
            ingress=IngressSpec(
                enabled=True,
                hostname="test.odoo.example.com",
                className="nginx",
                tls=True
            ),
            env=[
                {"name": "ODOO_ADMIN_PASSWORD", "valueFrom": {"secretKeyRef": {"name": "odoo-admin-secret", "key": "password"}}},
                {"name": "TZ", "value": "America/New_York"}
            ]
        )
    )
    
    assert instance.spec.image == "custom/odoo:17.0"
    assert instance.spec.replicas == 2
    assert instance.spec.resources.limits["cpu"] == "2"
    assert instance.spec.database["storageSize"] == "10Gi"
    assert instance.spec.filestore["storageSize"] == "20Gi"
    assert len(instance.spec.addons) == 2
    assert instance.spec.ingress.hostname == "test.odoo.example.com"
    assert len(instance.spec.env) == 2
    assert instance.spec.env[0]["name"] == "ODOO_ADMIN_PASSWORD"
