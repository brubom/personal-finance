import os
from typing import Optional

from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

def setup_telemetry(service_name: str) -> None:
    """Configure OpenTelemetry for the service.
    
    Args:
        service_name: Name of the service for resource attributes
    """
    # Create a resource with service information
    resource = Resource.create({
        "service.name": service_name,
        "service.version": os.getenv("K_REVISION", "dev"),
        "deployment.environment": os.getenv("ENVIRONMENT", "development")
    })
    
    # Create and set the tracer provider
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    
    # Add Cloud Trace exporter
    cloud_trace_exporter = CloudTraceSpanExporter(
        project_id=os.getenv("GOOGLE_CLOUD_PROJECT")
    )
    span_processor = SimpleSpanProcessor(cloud_trace_exporter)
    tracer_provider.add_span_processor(span_processor)

def get_current_trace_id() -> Optional[str]:
    """Get the current trace ID if available.
    
    Returns:
        The current trace ID as a string, or None if no active trace
    """
    current_span = trace.get_current_span()
    if current_span.is_recording():
        return current_span.get_span_context().trace_id.hex()
    return None

def create_span(name: str, attributes: dict = None) -> trace.Span:
    """Create a new span with the given name and attributes.
    
    Args:
        name: Name of the span
        attributes: Optional dictionary of attributes to add to the span
        
    Returns:
        The created span
    """
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span(name, attributes=attributes) as span:
        return span 