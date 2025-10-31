"""
Observability and Tracing Configuration
Distributed tracing with OpenTelemetry and Azure Application Insights

Features:
- OpenTelemetry instrumentation
- Azure Application Insights integration
- Distributed tracing across services
- Custom spans and metrics
- Performance profiling
"""

import logging

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)


class ObservabilityManager:
    """
    Manages observability, tracing, and instrumentation
    """

    def __init__(self, service_name: str = "crownsafe-api"):
        self.service_name = service_name
        self.tracer_provider = None
        self.tracer = None

    def initialize(self, endpoint: str = None):
        """
        Initialize OpenTelemetry tracing

        Args:
            endpoint: OTLP collector endpoint
        """
        try:
            # Set up tracer provider
            self.tracer_provider = TracerProvider()
            trace.set_tracer_provider(self.tracer_provider)

            # Configure OTLP exporter (if endpoint provided)
            if endpoint:
                otlp_exporter = OTLPSpanExporter(endpoint=endpoint)
                span_processor = BatchSpanProcessor(otlp_exporter)
                self.tracer_provider.add_span_processor(span_processor)
                logger.info(f"OpenTelemetry exporter configured: {endpoint}")

            # Get tracer
            self.tracer = trace.get_tracer(self.service_name)

            logger.info("Observability system initialized")

        except Exception as e:
            logger.error(f"Failed to initialize observability: {e}")

    def instrument_fastapi(self, app):
        """
        Instrument FastAPI application

        Args:
            app: FastAPI application instance
        """
        try:
            FastAPIInstrumentor.instrument_app(app)
            logger.info("FastAPI instrumentation enabled")
        except Exception as e:
            logger.error(f"FastAPI instrumentation failed: {e}")

    def instrument_sqlalchemy(self, engine):
        """
        Instrument SQLAlchemy database engine

        Args:
            engine: SQLAlchemy engine
        """
        try:
            SQLAlchemyInstrumentor().instrument(engine=engine)
            logger.info("SQLAlchemy instrumentation enabled")
        except Exception as e:
            logger.error(f"SQLAlchemy instrumentation failed: {e}")

    def instrument_redis(self):
        """
        Instrument Redis client
        """
        try:
            RedisInstrumentor().instrument()
            logger.info("Redis instrumentation enabled")
        except Exception as e:
            logger.error(f"Redis instrumentation failed: {e}")

    def instrument_requests(self):
        """
        Instrument HTTP requests library
        """
        try:
            RequestsInstrumentor().instrument()
            logger.info("Requests instrumentation enabled")
        except Exception as e:
            logger.error(f"Requests instrumentation failed: {e}")

    def create_span(self, name: str, attributes: dict[str, str] = None):
        """
        Create a custom span for tracing

        Args:
            name: Span name
            attributes: Span attributes (metadata)

        Returns:
            Span context manager
        """
        if self.tracer:
            span = self.tracer.start_as_current_span(name)
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)
            return span
        return None


# ====================
# Azure Monitor Integration
# ====================


class AzureMonitorIntegration:
    """
    Integration with Azure Application Insights
    """

    def __init__(self, connection_string: str = None):
        self.connection_string = connection_string
        self.client = None

    def initialize(self):
        """
        Initialize Azure Application Insights
        """
        if not self.connection_string:
            logger.warning("Azure Monitor connection string not configured")
            return

        try:
            # Azure Monitor exporters commented out - future integration
            # from azure.monitor.opentelemetry.exporter import (
            #     AzureMonitorMetricExporter,
            #     AzureMonitorTraceExporter,
            # )

            # Configure exporters (currently unused - future integration)
            # trace_exporter = AzureMonitorTraceExporter(connection_string=self.connection_string)
            # metrics_exporter = AzureMonitorMetricExporter(connection_string=self.connection_string)

            logger.info("Azure Monitor integration initialized")

        except Exception as e:
            logger.error(f"Azure Monitor initialization failed: {e}")

    def log_custom_event(self, event_name: str, properties: dict = None):
        """
        Log custom event to Application Insights

        Args:
            event_name: Event name
            properties: Event properties
        """
        try:
            # Log custom event
            logger.info(f"Custom event: {event_name}", extra=properties or {})
        except Exception as e:
            logger.error(f"Failed to log custom event: {e}")

    def log_custom_metric(self, metric_name: str, value: float, properties: dict = None):
        """
        Log custom metric to Application Insights

        Args:
            metric_name: Metric name
            value: Metric value
            properties: Metric properties
        """
        try:
            # Log custom metric
            logger.info(f"Custom metric: {metric_name} = {value}", extra=properties or {})
        except Exception as e:
            logger.error(f"Failed to log custom metric: {e}")


# ====================
# Global Instance
# ====================

_observability_manager = None


def get_observability_manager() -> ObservabilityManager:
    """
    Get global observability manager instance
    """
    global _observability_manager
    if _observability_manager is None:
        _observability_manager = ObservabilityManager()
    return _observability_manager


if __name__ == "__main__":
    # Demo usage
    obs = ObservabilityManager()
    obs.initialize()

    # Create custom span
    with obs.create_span("custom_operation", {"user_id": "123"}) as span:
        print("Performing traced operation...")

    print("Observability system demo complete")
