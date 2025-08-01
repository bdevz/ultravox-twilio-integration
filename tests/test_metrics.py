"""
Tests for metrics collection system.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from app.metrics import (
    MetricsCollector,
    MetricEvent,
    APICallMetrics,
    ServiceMetrics,
    get_metrics_collector,
    track_api_call,
    record_metric,
    record_request_metric
)


class TestMetricsCollector:
    """Test cases for MetricsCollector class."""
    
    def test_init(self):
        """Test metrics collector initialization."""
        collector = MetricsCollector(max_events=100, max_api_calls=50)
        
        assert collector.max_events == 100
        assert collector.max_api_calls == 50
        assert len(collector._events) == 0
        assert len(collector._api_calls) == 0
        assert len(collector._service_metrics) == 0
        assert len(collector._endpoint_metrics) == 0
    
    def test_record_event(self):
        """Test recording metric events."""
        collector = MetricsCollector()
        
        # Record an event
        collector.record_event(
            name="test_metric",
            value=42.5,
            tags={"service": "test"},
            correlation_id="test-123"
        )
        
        # Verify event was recorded
        assert len(collector._events) == 1
        event = collector._events[0]
        assert event.name == "test_metric"
        assert event.value == 42.5
        assert event.tags == {"service": "test"}
        assert event.correlation_id == "test-123"
        assert isinstance(event.timestamp, datetime)
    
    def test_record_api_call(self):
        """Test recording API call metrics."""
        collector = MetricsCollector()
        
        # Record an API call
        collector.record_api_call(
            endpoint="/api/agents",
            method="POST",
            service="ultravox",
            duration_ms=150.5,
            status_code=201,
            success=True,
            correlation_id="test-456"
        )
        
        # Verify API call was recorded
        assert len(collector._api_calls) == 1
        api_call = collector._api_calls[0]
        assert api_call.endpoint == "/api/agents"
        assert api_call.method == "POST"
        assert api_call.service == "ultravox"
        assert api_call.duration_ms == 150.5
        assert api_call.status_code == 201
        assert api_call.success is True
        assert api_call.correlation_id == "test-456"
        
        # Verify service metrics were updated
        service_metrics = collector._service_metrics["ultravox"]
        assert service_metrics.total_calls == 1
        assert service_metrics.successful_calls == 1
        assert service_metrics.failed_calls == 0
        assert service_metrics.total_duration_ms == 150.5
        assert service_metrics.avg_duration_ms == 150.5
        assert service_metrics.min_duration_ms == 150.5
        assert service_metrics.max_duration_ms == 150.5
        assert service_metrics.status_code_counts[201] == 1
    
    def test_record_failed_api_call(self):
        """Test recording failed API call metrics."""
        collector = MetricsCollector()
        
        # Record a failed API call
        collector.record_api_call(
            endpoint="/api/agents",
            method="POST",
            service="ultravox",
            duration_ms=75.0,
            status_code=500,
            success=False,
            error_type="ServerError"
        )
        
        # Verify service metrics were updated correctly
        service_metrics = collector._service_metrics["ultravox"]
        assert service_metrics.total_calls == 1
        assert service_metrics.successful_calls == 0
        assert service_metrics.failed_calls == 1
        assert service_metrics.error_count_by_type["ServerError"] == 1
        assert service_metrics.status_code_counts[500] == 1
    
    def test_record_request(self):
        """Test recording HTTP request metrics."""
        collector = MetricsCollector()
        
        # Record requests
        collector.record_request("GET", "/api/agents", 200)
        collector.record_request("POST", "/api/agents", 201)
        collector.record_request("GET", "/api/agents", 404)
        
        # Verify request counts
        assert collector._request_counts["GET:/api/agents"] == 2
        assert collector._request_counts["POST:/api/agents"] == 1
        assert collector._error_counts["404"] == 1
    
    def test_get_service_metrics(self):
        """Test retrieving service metrics."""
        collector = MetricsCollector()
        
        # Record some API calls
        collector.record_api_call("/api/agents", "POST", "ultravox", 100.0, 201, True)
        collector.record_api_call("/api/agents", "GET", "ultravox", 50.0, 200, True)
        collector.record_api_call("/api/calls", "POST", "twilio", 200.0, 500, False, "ServerError")
        
        # Get service metrics
        ultravox_metrics = collector.get_service_metrics("ultravox")
        twilio_metrics = collector.get_service_metrics("twilio")
        nonexistent_metrics = collector.get_service_metrics("nonexistent")
        
        # Verify ultravox metrics
        assert ultravox_metrics is not None
        assert ultravox_metrics.total_calls == 2
        assert ultravox_metrics.successful_calls == 2
        assert ultravox_metrics.failed_calls == 0
        assert ultravox_metrics.avg_duration_ms == 75.0
        
        # Verify twilio metrics
        assert twilio_metrics is not None
        assert twilio_metrics.total_calls == 1
        assert twilio_metrics.successful_calls == 0
        assert twilio_metrics.failed_calls == 1
        assert twilio_metrics.error_count_by_type["ServerError"] == 1
        
        # Verify nonexistent service
        assert nonexistent_metrics is None
    
    def test_get_endpoint_metrics(self):
        """Test retrieving endpoint metrics."""
        collector = MetricsCollector()
        
        # Record API calls to same endpoint
        collector.record_api_call("/api/agents", "POST", "ultravox", 100.0, 201, True)
        collector.record_api_call("/api/agents", "POST", "ultravox", 150.0, 201, True)
        
        # Get endpoint metrics
        endpoint_metrics = collector.get_endpoint_metrics("POST", "/api/agents")
        nonexistent_metrics = collector.get_endpoint_metrics("GET", "/nonexistent")
        
        # Verify endpoint metrics
        assert endpoint_metrics is not None
        assert endpoint_metrics.total_calls == 2
        assert endpoint_metrics.successful_calls == 2
        assert endpoint_metrics.avg_duration_ms == 125.0
        
        # Verify nonexistent endpoint
        assert nonexistent_metrics is None
    
    def test_get_all_metrics(self):
        """Test retrieving all metrics."""
        collector = MetricsCollector()
        
        # Record some data
        collector.record_event("test_metric", 42.0)
        collector.record_api_call("/api/agents", "POST", "ultravox", 100.0, 201, True)
        collector.record_request("GET", "/api/health", 200)
        
        # Get all metrics
        all_metrics = collector.get_all_metrics()
        
        # Verify structure
        assert "timestamp" in all_metrics
        assert "uptime_seconds" in all_metrics
        assert "application" in all_metrics
        assert "services" in all_metrics
        assert "endpoints" in all_metrics
        
        # Verify application metrics
        app_metrics = all_metrics["application"]
        assert app_metrics["total_requests"] == 1
        assert app_metrics["total_events"] == 1
        assert app_metrics["total_api_calls"] == 1
        
        # Verify service metrics
        assert "ultravox" in all_metrics["services"]
        ultravox_metrics = all_metrics["services"]["ultravox"]
        assert ultravox_metrics["total_calls"] == 1
        assert ultravox_metrics["success_rate"] == 1.0
        
        # Verify endpoint metrics
        assert "POST:/api/agents" in all_metrics["endpoints"]
    
    def test_get_recent_events(self):
        """Test retrieving recent events."""
        collector = MetricsCollector()
        
        # Record multiple events
        for i in range(5):
            collector.record_event(f"metric_{i}", float(i))
        
        # Get recent events
        recent_events = collector.get_recent_events(limit=3)
        
        # Verify we got the most recent events
        assert len(recent_events) == 3
        assert recent_events[0]["name"] == "metric_2"  # Most recent first
        assert recent_events[1]["name"] == "metric_3"
        assert recent_events[2]["name"] == "metric_4"
        
        # Verify event structure
        event = recent_events[0]
        assert "name" in event
        assert "value" in event
        assert "timestamp" in event
        assert "tags" in event
        assert "correlation_id" in event
    
    def test_get_recent_api_calls(self):
        """Test retrieving recent API calls."""
        collector = MetricsCollector()
        
        # Record multiple API calls
        for i in range(3):
            collector.record_api_call(f"/api/endpoint_{i}", "GET", "test", 100.0, 200, True)
        
        # Get recent API calls
        recent_calls = collector.get_recent_api_calls(limit=2)
        
        # Verify we got the most recent calls
        assert len(recent_calls) == 2
        assert recent_calls[0]["endpoint"] == "/api/endpoint_1"  # Most recent first
        assert recent_calls[1]["endpoint"] == "/api/endpoint_2"
        
        # Verify call structure
        call = recent_calls[0]
        assert "endpoint" in call
        assert "method" in call
        assert "service" in call
        assert "duration_ms" in call
        assert "status_code" in call
        assert "success" in call
        assert "timestamp" in call
    
    def test_reset_metrics(self):
        """Test resetting all metrics."""
        collector = MetricsCollector()
        
        # Record some data
        collector.record_event("test_metric", 42.0)
        collector.record_api_call("/api/agents", "POST", "ultravox", 100.0, 201, True)
        collector.record_request("GET", "/api/health", 200)
        
        # Verify data exists
        assert len(collector._events) > 0
        assert len(collector._api_calls) > 0
        assert len(collector._service_metrics) > 0
        assert len(collector._request_counts) > 0
        
        # Reset metrics
        collector.reset_metrics()
        
        # Verify everything is cleared
        assert len(collector._events) == 0
        assert len(collector._api_calls) == 0
        assert len(collector._service_metrics) == 0
        assert len(collector._endpoint_metrics) == 0
        assert len(collector._request_counts) == 0
        assert len(collector._error_counts) == 0


class TestTrackApiCall:
    """Test cases for track_api_call context manager."""
    
    @pytest.mark.asyncio
    async def test_successful_api_call_tracking(self):
        """Test tracking successful API calls."""
        collector = get_metrics_collector()
        collector.reset_metrics()  # Start fresh
        
        async with track_api_call("/test", "GET", "test_service") as context:
            context["status_code"] = 200
            # Simulate some work
            await asyncio.sleep(0.01)
        
        # Verify metrics were recorded
        assert len(collector._api_calls) == 1
        api_call = collector._api_calls[0]
        assert api_call.endpoint == "/test"
        assert api_call.method == "GET"
        assert api_call.service == "test_service"
        assert api_call.success is True
        assert api_call.status_code == 200
        assert api_call.duration_ms > 0
    
    @pytest.mark.asyncio
    async def test_failed_api_call_tracking(self):
        """Test tracking failed API calls."""
        collector = get_metrics_collector()
        collector.reset_metrics()  # Start fresh
        
        with pytest.raises(ValueError):
            async with track_api_call("/test", "POST", "test_service") as context:
                context["status_code"] = 500
                raise ValueError("Test error")
        
        # Verify metrics were recorded for the failure
        assert len(collector._api_calls) == 1
        api_call = collector._api_calls[0]
        assert api_call.endpoint == "/test"
        assert api_call.method == "POST"
        assert api_call.service == "test_service"
        assert api_call.success is False
        assert api_call.error_type == "ValueError"
        assert api_call.duration_ms > 0


class TestGlobalFunctions:
    """Test cases for global utility functions."""
    
    def test_record_metric(self):
        """Test global record_metric function."""
        collector = get_metrics_collector()
        collector.reset_metrics()  # Start fresh
        
        record_metric("test_metric", 123.45, {"tag": "value"}, "corr-123")
        
        # Verify metric was recorded
        assert len(collector._events) == 1
        event = collector._events[0]
        assert event.name == "test_metric"
        assert event.value == 123.45
        assert event.tags == {"tag": "value"}
        assert event.correlation_id == "corr-123"
    
    def test_record_request_metric(self):
        """Test global record_request_metric function."""
        collector = get_metrics_collector()
        collector.reset_metrics()  # Start fresh
        
        record_request_metric("POST", "/api/test", 201)
        
        # Verify request was recorded
        assert collector._request_counts["POST:/api/test"] == 1
    
    def test_get_metrics_collector_singleton(self):
        """Test that get_metrics_collector returns the same instance."""
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()
        
        assert collector1 is collector2


class TestServiceMetrics:
    """Test cases for ServiceMetrics data class."""
    
    def test_service_metrics_initialization(self):
        """Test ServiceMetrics initialization with defaults."""
        metrics = ServiceMetrics()
        
        assert metrics.total_calls == 0
        assert metrics.successful_calls == 0
        assert metrics.failed_calls == 0
        assert metrics.total_duration_ms == 0.0
        assert metrics.avg_duration_ms == 0.0
        assert metrics.min_duration_ms == float('inf')
        assert metrics.max_duration_ms == 0.0
        assert metrics.error_count_by_type == {}
        assert metrics.status_code_counts == {}


class TestMetricEvent:
    """Test cases for MetricEvent data class."""
    
    def test_metric_event_creation(self):
        """Test MetricEvent creation."""
        timestamp = datetime.now(timezone.utc)
        event = MetricEvent(
            name="test_metric",
            value=42.0,
            timestamp=timestamp,
            tags={"service": "test"},
            correlation_id="test-123"
        )
        
        assert event.name == "test_metric"
        assert event.value == 42.0
        assert event.timestamp == timestamp
        assert event.tags == {"service": "test"}
        assert event.correlation_id == "test-123"


class TestAPICallMetrics:
    """Test cases for APICallMetrics data class."""
    
    def test_api_call_metrics_creation(self):
        """Test APICallMetrics creation."""
        timestamp = datetime.now(timezone.utc)
        metrics = APICallMetrics(
            endpoint="/api/test",
            method="POST",
            status_code=201,
            duration_ms=150.5,
            timestamp=timestamp,
            service="test_service",
            success=True,
            error_type=None,
            correlation_id="test-456"
        )
        
        assert metrics.endpoint == "/api/test"
        assert metrics.method == "POST"
        assert metrics.status_code == 201
        assert metrics.duration_ms == 150.5
        assert metrics.timestamp == timestamp
        assert metrics.service == "test_service"
        assert metrics.success is True
        assert metrics.error_type is None
        assert metrics.correlation_id == "test-456"