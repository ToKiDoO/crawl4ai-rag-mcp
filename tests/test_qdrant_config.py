"""
Configuration utilities for Qdrant integration tests.
Handles environment detection and setup for both Docker and localhost environments.
"""

import os
import requests
import time
from typing import Tuple, Dict, Any
import pytest


class QdrantTestConfig:
    """Configuration manager for Qdrant integration tests"""
    
    def __init__(self):
        self.environment = self._detect_environment()
        self.qdrant_url = self._get_qdrant_url()
        self.is_healthy = False
        self._check_qdrant_health()
    
    def _detect_environment(self) -> str:
        """Detect if we're running in Docker or localhost environment"""
        # Check for Docker environment indicators
        if os.path.exists('/.dockerenv'):
            return "docker"
        
        # Check environment variable
        if os.getenv("DOCKER_ENV", "").lower() == "true":
            return "docker"
        
        # Check if we can reach Docker internal network
        try:
            response = requests.get("http://qdrant:6333/healthz", timeout=2)
            if response.status_code == 200:
                return "docker"
        except:
            pass
        
        return "localhost"
    
    def _get_qdrant_url(self) -> str:
        """Get the appropriate Qdrant URL based on environment"""
        # First check if explicitly set in environment
        if "QDRANT_URL" in os.environ:
            return os.environ["QDRANT_URL"]
        
        # Otherwise use environment-specific defaults
        if self.environment == "docker":
            return "http://qdrant:6333"
        else:
            return "http://localhost:6333"
    
    def _check_qdrant_health(self) -> bool:
        """Check if Qdrant is healthy and responsive"""
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                health_url = f"{self.qdrant_url}/healthz"
                response = requests.get(health_url, timeout=5)
                
                if response.status_code == 200:
                    self.is_healthy = True
                    print(f"✓ Qdrant healthy at {self.qdrant_url} (environment: {self.environment})")
                    return True
                else:
                    print(f"✗ Qdrant health check failed: HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"✗ Qdrant connection attempt {attempt + 1}/{max_retries} failed: {e}")
                
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
        
        self.is_healthy = False
        return False
    
    def setup_environment_variables(self) -> Dict[str, str]:
        """Setup environment variables for Qdrant testing"""
        env_vars = {
            'VECTOR_DATABASE': 'qdrant',
            'QDRANT_URL': self.qdrant_url,
            'QDRANT_API_KEY': '',
            'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY', 'test-key'),
            'USE_RERANKING': 'false',
            'USE_HYBRID_SEARCH': 'false',
            'USE_CONTEXTUAL_EMBEDDINGS': 'false',
            'USE_AGENTIC_RAG': 'false',
            'MODEL_CHOICE': 'gpt-4.1-nano-2025-04-14'
        }
        
        # Set environment variables
        for key, value in env_vars.items():
            os.environ[key] = value
        
        return env_vars
    
    def get_skip_reason(self) -> str:
        """Get reason for skipping tests if Qdrant is not available"""
        if not self.is_healthy:
            if self.environment == "docker":
                return (
                    f"Qdrant not available at {self.qdrant_url}. "
                    f"Start with: docker-compose up -d qdrant"
                )
            else:
                return (
                    f"Qdrant not available at {self.qdrant_url}. "
                    f"Start with: docker run -p 6333:6333 qdrant/qdrant"
                )
        return ""
    
    def should_skip_tests(self) -> bool:
        """Check if tests should be skipped due to Qdrant unavailability"""
        return not self.is_healthy
    
    def get_test_summary(self) -> Dict[str, Any]:
        """Get summary of test configuration"""
        return {
            'environment': self.environment,
            'qdrant_url': self.qdrant_url,
            'qdrant_healthy': self.is_healthy,
            'docker_env': self.environment == "docker",
            'localhost_env': self.environment == "localhost"
        }


# Global test configuration instance
test_config = QdrantTestConfig()


def pytest_configure(config):
    """Configure pytest with Qdrant-specific settings"""
    # Add custom markers
    config.addinivalue_line(
        "markers", "qdrant: mark test as requiring Qdrant database"
    )
    config.addinivalue_line(
        "markers", "docker_env: mark test as requiring Docker environment"
    )
    config.addinivalue_line(
        "markers", "localhost_env: mark test as requiring localhost environment"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle environment-specific tests"""
    skip_qdrant = pytest.mark.skip(reason=test_config.get_skip_reason())
    skip_docker = pytest.mark.skip(reason="Not running in Docker environment")
    skip_localhost = pytest.mark.skip(reason="Not running in localhost environment")
    
    for item in items:
        # Skip Qdrant tests if Qdrant is not available
        if "qdrant" in item.keywords and test_config.should_skip_tests():
            item.add_marker(skip_qdrant)
        
        # Skip Docker-specific tests if not in Docker
        if "docker_env" in item.keywords and test_config.environment != "docker":
            item.add_marker(skip_docker)
        
        # Skip localhost-specific tests if not on localhost
        if "localhost_env" in item.keywords and test_config.environment != "localhost":
            item.add_marker(skip_localhost)


@pytest.fixture(scope="session")
def qdrant_config():
    """Provide Qdrant test configuration to tests"""
    test_config.setup_environment_variables()
    return test_config


@pytest.fixture(scope="session", autouse=True)
def setup_qdrant_environment():
    """Setup Qdrant environment for all tests"""
    print(f"\n{'='*60}")
    print("QDRANT TEST ENVIRONMENT SETUP")
    print(f"{'='*60}")
    
    summary = test_config.get_test_summary()
    for key, value in summary.items():
        print(f"{key.replace('_', ' ').title()}: {value}")
    
    if test_config.should_skip_tests():
        print(f"\n⚠️  WARNING: {test_config.get_skip_reason()}")
    else:
        print(f"\n✅ Qdrant is ready for testing")
    
    print(f"{'='*60}\n")
    
    # Setup environment variables
    test_config.setup_environment_variables()
    
    yield test_config
    
    print(f"\n{'='*60}")
    print("QDRANT TEST ENVIRONMENT CLEANUP")
    print(f"{'='*60}")


class QdrantTestMarkers:
    """Helper class for applying test markers"""
    
    @staticmethod
    def requires_qdrant(test_func):
        """Decorator to mark tests as requiring Qdrant"""
        return pytest.mark.qdrant(test_func)
    
    @staticmethod
    def docker_only(test_func):
        """Decorator to mark tests as Docker-only"""
        return pytest.mark.docker_env(test_func)
    
    @staticmethod
    def localhost_only(test_func):
        """Decorator to mark tests as localhost-only"""
        return pytest.mark.localhost_env(test_func)
    
    @staticmethod
    def integration(test_func):
        """Decorator to mark tests as integration tests"""
        return pytest.mark.integration(test_func)


# Convenience decorators
requires_qdrant = QdrantTestMarkers.requires_qdrant
docker_only = QdrantTestMarkers.docker_only
localhost_only = QdrantTestMarkers.localhost_only
integration = QdrantTestMarkers.integration


def get_qdrant_url() -> str:
    """Get the current Qdrant URL"""
    return test_config.qdrant_url


def is_qdrant_available() -> bool:
    """Check if Qdrant is available for testing"""
    return test_config.is_healthy


def get_environment() -> str:
    """Get the current test environment"""
    return test_config.environment


def wait_for_qdrant(timeout: int = 30) -> bool:
    """Wait for Qdrant to become available"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{test_config.qdrant_url}/healthz", timeout=2)
            if response.status_code == 200:
                test_config.is_healthy = True
                return True
        except:
            pass
        
        time.sleep(1)
    
    return False


# Environment detection helper functions
def is_docker_environment() -> bool:
    """Check if running in Docker environment"""
    return test_config.environment == "docker"


def is_localhost_environment() -> bool:
    """Check if running in localhost environment"""
    return test_config.environment == "localhost"