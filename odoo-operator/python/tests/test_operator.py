"""
Tests for the Odoo operator.
"""
import pytest
import kopf
from unittest.mock import patch, MagicMock
from ..operator import create_odoo_instance, update_odoo_instance, delete_odoo_instance


@pytest.fixture
def mock_k8s_apis():
    """Mock Kubernetes API clients"""
    with patch('kubernetes.client.CoreV1Api') as mock_core_v1, \
         patch('kubernetes.client.AppsV1Api') as mock_apps_v1, \
         patch('kubernetes.client.NetworkingV1Api') as mock_networking_v1, \
         patch('kubernetes.client.CustomObjectsApi') as mock_custom_objects:
        
        # Setup mock returns
        mock_custom_objects.return_value.get_namespaced_custom_object.return_value = {
            'metadata': {'uid': 'test-uid'}
        }
        
        yield {
            'core_v1': mock_core_v1.return_value,
            'apps_v1': mock_apps_v1.return_value,
            'networking_v1': mock_networking_v1.return_value,
            'custom_objects': mock_custom_objects.return_value
        }


def test_create_odoo_instance(mock_k8s_apis):
    """Test creating an Odoo instance"""
    # Test data
    meta = {'name': 'test', 'namespace': 'default'}
    spec = {
        'version': '17.0',
        'replicas': 1,
        'resources': {
            'limits': {'cpu': '2', 'memory': '4Gi'},
            'requests': {'cpu': '500m', 'memory': '1Gi'}
        },
        'database': {
            'storageSize': '10Gi',
            'storageClass': 'standard'
        },
        'filestore': {
            'storageSize': '20Gi',
            'storageClass': 'standard'
        },
        'ingress': {
            'enabled': True,
            'hostname': 'test.odoo.example.com',
            'tls': True
        }
    }
    
    # Call the handler
    result = create_odoo_instance(spec=spec, meta=meta, status={})
    
    # Verify the result
    assert result['status'] == 'success'
    
    # Verify API calls
    mock_k8s_apis['core_v1'].create_namespaced_persistent_volume_claim.assert_called_once()
    mock_k8s_apis['apps_v1'].create_namespaced_deployment.assert_called_once()
    mock_k8s_apis['core_v1'].create_namespaced_service.assert_called_once()
    mock_k8s_apis['networking_v1'].create_namespaced_ingress.assert_called_once()
    mock_k8s_apis['custom_objects'].patch_namespaced_custom_object_status.assert_called()


def test_update_odoo_instance(mock_k8s_apis):
    """Test updating an Odoo instance"""
    # Test data
    meta = {'name': 'test', 'namespace': 'default'}
    spec = {
        'version': '17.0',
        'replicas': 2,  # Changed from 1 to 2
        'resources': {
            'limits': {'cpu': '2', 'memory': '4Gi'},
            'requests': {'cpu': '500m', 'memory': '1Gi'}
        },
        'ingress': {
            'enabled': True,
            'hostname': 'new.odoo.example.com',  # Changed hostname
            'tls': True
        }
    }
    old = {
        'version': '17.0',
        'replicas': 1,
        'ingress': {
            'enabled': True,
            'hostname': 'test.odoo.example.com',
            'tls': True
        }
    }
    diff = [('change', ('spec', 'replicas'), 1, 2),
            ('change', ('spec', 'ingress', 'hostname'), 'test.odoo.example.com', 'new.odoo.example.com')]
    
    # Setup mock for existing deployment
    deployment = MagicMock()
    deployment.spec.replicas = 1
    mock_k8s_apis['apps_v1'].read_namespaced_deployment.return_value = deployment
    
    # Setup mock for existing ingress
    ingress = MagicMock()
    ingress.spec.rules = [MagicMock()]
    ingress.spec.rules[0].host = 'test.odoo.example.com'
    mock_k8s_apis['networking_v1'].read_namespaced_ingress.return_value = ingress
    
    # Call the handler
    result = update_odoo_instance(spec=spec, meta=meta, status={}, old=old, diff=diff)
    
    # Verify the result
    assert result['status'] == 'success'
    
    # Verify API calls
    mock_k8s_apis['apps_v1'].patch_namespaced_deployment.assert_called_once()
    mock_k8s_apis['networking_v1'].patch_namespaced_ingress.assert_called_once()
    mock_k8s_apis['custom_objects'].patch_namespaced_custom_object_status.assert_called()


def test_delete_odoo_instance():
    """Test deleting an Odoo instance"""
    # Test data
    meta = {'name': 'test', 'namespace': 'default'}
    spec = {'version': '17.0'}
    
    # Call the handler
    result = delete_odoo_instance(spec=spec, meta=meta, status={})
    
    # Verify the result
    assert result['status'] == 'success'
