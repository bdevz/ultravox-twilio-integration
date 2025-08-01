"""
Dependency injection container for the application.
"""

from functools import lru_cache
from typing import AsyncGenerator
import logging

logger = logging.getLogger(__name__)

class DependencyContainer:
    """
    Container for managing application dependencies and services.
    """
    
    def __init__(self):
        self._services = {}
    
    def register_service(self, service_name: str, service_instance):
        """Register a service instance in the container."""
        self._services[service_name] = service_instance
        logger.info(f"Registered service: {service_name}")
    
    def get_service(self, service_name: str):
        """Get a service instance from the container."""
        if service_name not in self._services:
            raise ValueError(f"Service {service_name} not registered")
        return self._services[service_name]

# Global dependency container instance
_container = DependencyContainer()

@lru_cache()
def get_dependency_container() -> DependencyContainer:
    """
    Get the global dependency container instance.
    
    Returns:
        DependencyContainer: The global container instance
    """
    return _container

async def get_container() -> AsyncGenerator[DependencyContainer, None]:
    """
    FastAPI dependency to get the dependency container.
    
    Yields:
        DependencyContainer: The dependency container instance
    """
    yield get_dependency_container()