"""
Metrics collection system for API calls and external service interactions.
"""

import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass, field
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from threading import Lock

from app.logging_config import get_correlation_id, LoggerMixin


logger = logging.getLogger(__name__)


@dataclass
class MetricEvent:
    """Represents a single metric event."""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    correlation_id: Optional[str] = None


@dataclass
class APICallMetrics:
    """Metrics for API calls."""
    endpoint: str
    method: str
    status_code: Optional[int]
    duration_ms: float
    timestamp: datetime
    service: str  # 'ultravox', 'twilio', 'internal'
    success: bool
    error_type: Optional[str] = None
    correlation_id: Optional[str] = None


@dataclass
class ServiceMetrics:
    """Aggregated metrics for a service."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    max_duration_ms: float = 0.0
    error_count_by_type: Dict[str, int] = field(default_factory=dict)
    status_code_counts: Dict[int, int] = field(default_factory=dict)


class MetricsCollector(LoggerMixin):
    """Collects and aggregates metrics for monitoring and observability."""
    
    def __init__(self, max_events: int = 10000, max_api_calls: int = 1000):
        """
        Initialize metrics collector.
        
        Args:
            max_events: Maximum number of metric events to keep in memory
            max_api_calls: Maximum number of API call metrics to keep in memory
        """
        self.max_events = max_events
        self.max_api_calls = max_api_calls
        
        # Thread-safe storage
        self._lock = Lock()
        self._events: deque = deque(maxlen=max_events)
        self._api_calls: deque = deque(maxlen=max_api_calls)
        
        # Aggregated metrics
        self._service_metrics: Dict[str, ServiceMetrics] = defaultdict(ServiceMetrics)
        self._endpoint_metrics: Dict[str, ServiceMetrics] = defaultdict(ServiceMetrics)
        
        # Application metrics
        self._app_start_time = datetime.now(timezone.utc)
        self._request_counts = defaultdict(int)
        self._error_counts = defaultdict(int)
    
    def record_event(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
        correlation_id: Optional[str] = None
    ) -> None:
        """
        Record a metric event.
        
        Args:
            name: Metric name
            value: Metric value
            tags: Optional tags for the metric
            correlation_id: Optional correlation ID
        """
        if correlation_id is None:
            correlation_id = get_correlation_id()
        
        event = MetricEvent(
            name=name,
            value=value,
            timestamp=datetime.now(timezone.utc),
            tags=tags or {},
            correlation_id=correlation_id
        )
        
        with self._lock:
            self._events.append(event)
        
        # Log the metric event
        self.logger.info(
            f"Metric recorded: {name}",
            extra={
                "metric_name": name,
                "metric_value": value,
                "metric_tags": tags or {},
                "correlation_id": correlation_id
            }
        )
    
    def record_api_call(
        self,
        endpoint: str,
        method: str,
        service: str,
        duration_ms: float,
        status_code: Optional[int] = None,
        success: bool = True,
        error_type: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> None:
        """
        Record an API call metric.
        
        Args:
            endpoint: API endpoint
            method: HTTP method
            service: Service name ('ultravox', 'twilio', 'internal')
            duration_ms: Call duration in milliseconds
            status_code: HTTP status code
            success: Whether the call was successful
            error_type: Type of error if call failed
            correlation_id: Optional correlation ID
        """
        if correlation_id is None:
            correlation_id = get_correlation_id()
        
        api_call = APICallMetrics(
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration_ms=duration_ms,
            timestamp=datetime.now(timezone.utc),
            service=service,
            success=success,
            error_type=error_type,
            correlation_id=correlation_id
        )
        
        with self._lock:
            self._api_calls.append(api_call)
            self._update_aggregated_metrics(api_call)
        
        # Log the API call metric
        self.logger.info(
            f"API call recorded: {method} {endpoint}",
            extra={
                "api_endpoint": endpoint,
                "api_method": method,
                "api_service": service,
                "api_duration_ms": duration_ms,
                "api_status_code": status_code,
                "api_success": success,
                "api_error_type": error_type,
                "correlation_id": correlation_id
            }
        )
    
    def _update_aggregated_metrics(self, api_call: APICallMetrics) -> None:
        """
        Update aggregated metrics with new API call data.
        
        Args:
            api_call: API call metrics to aggregate
        """
        # Update service metrics
        service_metrics = self._service_metrics[api_call.service]
        self._update_service_metrics(service_metrics, api_call)
        
        # Update endpoint metrics
        endpoint_key = f"{api_call.method}:{api_call.endpoint}"
        endpoint_metrics = self._endpoint_metrics[endpoint_key]
        self._update_service_metrics(endpoint_metrics, api_call)
    
    def _update_service_metrics(self, metrics: ServiceMetrics, api_call: APICallMetrics) -> None:
        """
        Update service metrics with API call data.
        
        Args:
            metrics: Service metrics to update
            api_call: API call data
        """
        metrics.total_calls += 1
        
        if api_call.success:
            metrics.successful_calls += 1
        else:
            metrics.failed_calls += 1
            if api_call.error_type:
                metrics.error_count_by_type[api_call.error_type] = (
                    metrics.error_count_by_type.get(api_call.error_type, 0) + 1
                )
        
        if api_call.status_code:
            metrics.status_code_counts[api_call.status_code] = (
                metrics.status_code_counts.get(api_call.status_code, 0) + 1
            )
        
        # Update duration metrics
        metrics.total_duration_ms += api_call.duration_ms
        metrics.avg_duration_ms = metrics.total_duration_ms / metrics.total_calls
        metrics.min_duration_ms = min(metrics.min_duration_ms, api_call.duration_ms)
        metrics.max_duration_ms = max(metrics.max_duration_ms, api_call.duration_ms)
    
    def record_request(self, method: str, path: str, status_code: int) -> None:
        """
        Record an HTTP request.
        
        Args:
            method: HTTP method
            path: Request path
            status_code: Response status code
        """
        with self._lock:
            self._request_counts[f"{method}:{path}"] += 1
            if status_code >= 400:
                self._error_counts[f"{status_code}"] += 1
    
    def get_service_metrics(self, service: str) -> Optional[ServiceMetrics]:
        """
        Get aggregated metrics for a service.
        
        Args:
            service: Service name
            
        Returns:
            ServiceMetrics: Aggregated metrics or None if service not found
        """
        with self._lock:
            return self._service_metrics.get(service)
    
    def get_endpoint_metrics(self, method: str, endpoint: str) -> Optional[ServiceMetrics]:
        """
        Get aggregated metrics for an endpoint.
        
        Args:
            method: HTTP method
            endpoint: Endpoint path
            
        Returns:
            ServiceMetrics: Aggregated metrics or None if endpoint not found
        """
        endpoint_key = f"{method}:{endpoint}"
        with self._lock:
            return self._endpoint_metrics.get(endpoint_key)
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get all collected metrics.
        
        Returns:
            dict: All metrics data
        """
        with self._lock:
            uptime_seconds = (datetime.now(timezone.utc) - self._app_start_time).total_seconds()
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "uptime_seconds": uptime_seconds,
                "application": {
                    "total_requests": sum(self._request_counts.values()),
                    "request_counts_by_endpoint": dict(self._request_counts),
                    "error_counts_by_status": dict(self._error_counts),
                    "total_events": len(self._events),
                    "total_api_calls": len(self._api_calls)
                },
                "services": {
                    service: {
                        "total_calls": metrics.total_calls,
                        "successful_calls": metrics.successful_calls,
                        "failed_calls": metrics.failed_calls,
                        "success_rate": (
                            metrics.successful_calls / metrics.total_calls 
                            if metrics.total_calls > 0 else 0.0
                        ),
                        "avg_duration_ms": metrics.avg_duration_ms,
                        "min_duration_ms": metrics.min_duration_ms if metrics.min_duration_ms != float('inf') else 0.0,
                        "max_duration_ms": metrics.max_duration_ms,
                        "error_count_by_type": dict(metrics.error_count_by_type),
                        "status_code_counts": dict(metrics.status_code_counts)
                    }
                    for service, metrics in self._service_metrics.items()
                },
                "endpoints": {
                    endpoint: {
                        "total_calls": metrics.total_calls,
                        "successful_calls": metrics.successful_calls,
                        "failed_calls": metrics.failed_calls,
                        "success_rate": (
                            metrics.successful_calls / metrics.total_calls 
                            if metrics.total_calls > 0 else 0.0
                        ),
                        "avg_duration_ms": metrics.avg_duration_ms,
                        "min_duration_ms": metrics.min_duration_ms if metrics.min_duration_ms != float('inf') else 0.0,
                        "max_duration_ms": metrics.max_duration_ms
                    }
                    for endpoint, metrics in self._endpoint_metrics.items()
                }
            }
    
    def get_recent_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent metric events.
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            list: Recent metric events
        """
        with self._lock:
            events = list(self._events)[-limit:]
            return [
                {
                    "name": event.name,
                    "value": event.value,
                    "timestamp": event.timestamp.isoformat(),
                    "tags": event.tags,
                    "correlation_id": event.correlation_id
                }
                for event in events
            ]
    
    def get_recent_api_calls(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent API call metrics.
        
        Args:
            limit: Maximum number of API calls to return
            
        Returns:
            list: Recent API call metrics
        """
        with self._lock:
            api_calls = list(self._api_calls)[-limit:]
            return [
                {
                    "endpoint": call.endpoint,
                    "method": call.method,
                    "service": call.service,
                    "duration_ms": call.duration_ms,
                    "status_code": call.status_code,
                    "success": call.success,
                    "error_type": call.error_type,
                    "timestamp": call.timestamp.isoformat(),
                    "correlation_id": call.correlation_id
                }
                for call in api_calls
            ]
    
    def reset_metrics(self) -> None:
        """Reset all collected metrics."""
        with self._lock:
            self._events.clear()
            self._api_calls.clear()
            self._service_metrics.clear()
            self._endpoint_metrics.clear()
            self._request_counts.clear()
            self._error_counts.clear()
            self._app_start_time = datetime.now(timezone.utc)
        
        self.logger.info("All metrics have been reset")


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """
    Get the global metrics collector instance.
    
    Returns:
        MetricsCollector: The metrics collector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


@asynccontextmanager
async def track_api_call(
    endpoint: str,
    method: str,
    service: str,
    correlation_id: Optional[str] = None
):
    """
    Context manager to track API call metrics.
    
    Args:
        endpoint: API endpoint
        method: HTTP method
        service: Service name
        correlation_id: Optional correlation ID
        
    Yields:
        dict: Context data for the API call
    """
    if correlation_id is None:
        correlation_id = get_correlation_id()
    
    start_time = time.time()
    context = {
        "endpoint": endpoint,
        "method": method,
        "service": service,
        "correlation_id": correlation_id,
        "start_time": start_time
    }
    
    try:
        yield context
        
        # Record successful call
        duration_ms = (time.time() - start_time) * 1000
        get_metrics_collector().record_api_call(
            endpoint=endpoint,
            method=method,
            service=service,
            duration_ms=duration_ms,
            status_code=context.get("status_code"),
            success=True,
            correlation_id=correlation_id
        )
        
    except Exception as e:
        # Record failed call
        duration_ms = (time.time() - start_time) * 1000
        get_metrics_collector().record_api_call(
            endpoint=endpoint,
            method=method,
            service=service,
            duration_ms=duration_ms,
            status_code=context.get("status_code"),
            success=False,
            error_type=type(e).__name__,
            correlation_id=correlation_id
        )
        raise


def record_metric(
    name: str,
    value: float,
    tags: Optional[Dict[str, str]] = None,
    correlation_id: Optional[str] = None
) -> None:
    """
    Record a metric event.
    
    Args:
        name: Metric name
        value: Metric value
        tags: Optional tags
        correlation_id: Optional correlation ID
    """
    get_metrics_collector().record_event(name, value, tags, correlation_id)


def record_request_metric(method: str, path: str, status_code: int) -> None:
    """
    Record an HTTP request metric.
    
    Args:
        method: HTTP method
        path: Request path
        status_code: Response status code
    """
    get_metrics_collector().record_request(method, path, status_code)