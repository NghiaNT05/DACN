"""Graph builder - creates service dependency graph from various sources.

Supports building graph from:
- Kubernetes deployments/services
- OpenTelemetry traces
- Manual configuration
"""

import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from .schema import (
    ServiceNode,
    DependencyEdge,
    ServiceGraph,
    ServiceType,
    DependencyType,
    Protocol,
)

logger = logging.getLogger(__name__)


# Known service type mappings
SERVICE_TYPE_KEYWORDS = {
    ServiceType.FRONTEND: ["frontend", "web", "ui", "client"],
    ServiceType.DATABASE: ["postgres", "mysql", "mongo", "redis", "opensearch", "elasticsearch"],
    ServiceType.QUEUE: ["kafka", "rabbitmq", "nats", "pulsar"],
    ServiceType.CACHE: ["redis", "memcached", "cache"],
    ServiceType.GATEWAY: ["gateway", "ingress", "nginx", "envoy", "proxy"],
}

# Protocol detection patterns
PROTOCOL_PATTERNS = {
    Protocol.GRPC: ["grpc", "protobuf"],
    Protocol.KAFKA: ["kafka"],
    Protocol.REDIS: ["redis"],
    Protocol.POSTGRES: ["postgres", "postgresql", "pg"],
    Protocol.MONGODB: ["mongo"],
}


def detect_service_type(name: str, image: Optional[str] = None) -> ServiceType:
    """Detect service type from name/image."""
    text = f"{name} {image or ''}".lower()
    
    for stype, keywords in SERVICE_TYPE_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return stype
    
    return ServiceType.BACKEND


def detect_protocol(target_name: str, metadata: Optional[Dict] = None) -> Protocol:
    """Detect protocol from target service name."""
    text = target_name.lower()
    
    for protocol, patterns in PROTOCOL_PATTERNS.items():
        if any(p in text for p in patterns):
            return protocol
    
    return Protocol.HTTP


class GraphBuilder:
    """Builds service dependency graph from various sources."""
    
    def __init__(self):
        """Initialize builder."""
        self.graph = ServiceGraph()
    
    def build_from_otel_demo(self) -> ServiceGraph:
        """Build graph for OpenTelemetry demo application.
        
        This is a predefined graph based on the known architecture
        of the OpenTelemetry demo application.
        
        Returns:
            ServiceGraph for OTEL demo
        """
        self.graph = ServiceGraph(
            name="otel_demo_graph",
            source="opentelemetry-demo",
        )
        
        # Define all services
        services = [
            # Frontend
            ("frontend", "Frontend", ServiceType.FRONTEND, "typescript"),
            ("frontendproxy", "Frontend Proxy", ServiceType.GATEWAY, "envoy"),
            ("loadgenerator", "Load Generator", ServiceType.WORKER, "python"),
            
            # Core services
            ("cart", "Cart Service", ServiceType.BACKEND, "dotnet"),
            ("checkout", "Checkout Service", ServiceType.BACKEND, "go"),
            ("currency", "Currency Service", ServiceType.BACKEND, "cpp"),
            ("email", "Email Service", ServiceType.BACKEND, "ruby"),
            ("payment", "Payment Service", ServiceType.BACKEND, "javascript"),
            ("productcatalog", "Product Catalog", ServiceType.BACKEND, "go"),
            ("recommendation", "Recommendation", ServiceType.BACKEND, "python"),
            ("shipping", "Shipping Service", ServiceType.BACKEND, "rust"),
            ("quote", "Quote Service", ServiceType.BACKEND, "php"),
            ("ad", "Ad Service", ServiceType.BACKEND, "java"),
            ("fraud", "Fraud Detection", ServiceType.BACKEND, "kotlin"),
            ("accounting", "Accounting Service", ServiceType.BACKEND, "go"),
            ("flagd", "Feature Flag", ServiceType.BACKEND, "go"),
            
            # Data stores
            ("redis-cart", "Redis Cart", ServiceType.CACHE, None),
            ("kafka", "Kafka", ServiceType.QUEUE, None),
            ("postgres", "PostgreSQL", ServiceType.DATABASE, None),
            ("opensearch", "OpenSearch", ServiceType.DATABASE, None),
            
            # Observability
            ("otelcol", "OTel Collector", ServiceType.WORKER, "go"),
            ("jaeger", "Jaeger", ServiceType.BACKEND, "go"),
            ("prometheus", "Prometheus", ServiceType.BACKEND, "go"),
            ("grafana", "Grafana", ServiceType.FRONTEND, None),
        ]
        
        for sid, name, stype, lang in services:
            self.graph.add_node(ServiceNode(
                id=sid,
                name=name,
                service_type=stype,
                language=lang,
            ))
        
        # Define dependencies (source -> target)
        dependencies = [
            # Frontend dependencies
            ("frontend", "productcatalog", DependencyType.CALLS),
            ("frontend", "currency", DependencyType.CALLS),
            ("frontend", "cart", DependencyType.CALLS),
            ("frontend", "checkout", DependencyType.CALLS),
            ("frontend", "shipping", DependencyType.CALLS),
            ("frontend", "recommendation", DependencyType.CALLS),
            ("frontend", "ad", DependencyType.CALLS),
            
            # Checkout flow (critical path)
            ("checkout", "cart", DependencyType.CALLS),
            ("checkout", "productcatalog", DependencyType.CALLS),
            ("checkout", "currency", DependencyType.CALLS),
            ("checkout", "payment", DependencyType.CALLS),
            ("checkout", "shipping", DependencyType.CALLS),
            ("checkout", "email", DependencyType.CALLS),
            ("checkout", "kafka", DependencyType.PUBLISHES_TO),
            
            # Cart
            ("cart", "redis-cart", DependencyType.READS_FROM),
            ("cart", "redis-cart", DependencyType.WRITES_TO),
            
            # Recommendation
            ("recommendation", "productcatalog", DependencyType.CALLS),
            ("recommendation", "flagd", DependencyType.CALLS),
            
            # Ad service
            ("ad", "flagd", DependencyType.CALLS),
            
            # Shipping
            ("shipping", "quote", DependencyType.CALLS),
            
            # Kafka consumers
            ("accounting", "kafka", DependencyType.CONSUMES_FROM),
            ("fraud", "kafka", DependencyType.CONSUMES_FROM),
            
            # Observability
            ("frontend", "otelcol", DependencyType.CALLS),
            ("cart", "otelcol", DependencyType.CALLS),
            ("checkout", "otelcol", DependencyType.CALLS),
            ("otelcol", "jaeger", DependencyType.CALLS),
            ("otelcol", "prometheus", DependencyType.CALLS),
            ("grafana", "prometheus", DependencyType.READS_FROM),
            
            # Proxy
            ("frontendproxy", "frontend", DependencyType.CALLS),
            ("loadgenerator", "frontendproxy", DependencyType.CALLS),
        ]
        
        for source, target, dep_type in dependencies:
            protocol = detect_protocol(target)
            is_critical = source == "checkout" or target in ["payment", "cart"]
            
            self.graph.add_edge(DependencyEdge(
                source_id=source,
                target_id=target,
                dependency_type=dep_type,
                protocol=protocol,
                is_critical=is_critical,
            ))
        
        logger.info(f"Built OTEL demo graph: {self.graph.stats()}")
        return self.graph
    
    def build_from_kubernetes(self, deployments: List[Dict], services: List[Dict]) -> ServiceGraph:
        """Build graph from Kubernetes resources.
        
        Args:
            deployments: List of K8s Deployment dicts
            services: List of K8s Service dicts
            
        Returns:
            ServiceGraph
        """
        self.graph = ServiceGraph(source="kubernetes")
        
        # Add nodes from deployments
        for deploy in deployments:
            metadata = deploy.get("metadata", {})
            spec = deploy.get("spec", {})
            
            name = metadata.get("name", "unknown")
            namespace = metadata.get("namespace", "default")
            
            # Get container info
            containers = spec.get("template", {}).get("spec", {}).get("containers", [])
            image = containers[0].get("image") if containers else None
            
            # Get resource limits
            resources = containers[0].get("resources", {}) if containers else {}
            limits = resources.get("limits", {})
            
            node = ServiceNode(
                id=name,
                name=name,
                namespace=namespace,
                service_type=detect_service_type(name, image),
                image=image,
                replicas=spec.get("replicas", 1),
                cpu_limit=limits.get("cpu"),
                memory_limit=limits.get("memory"),
                labels=metadata.get("labels", {}),
            )
            
            self.graph.add_node(node)
        
        # Infer dependencies from environment variables
        for deploy in deployments:
            source_name = deploy.get("metadata", {}).get("name")
            containers = deploy.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
            
            for container in containers:
                env_vars = container.get("env", [])
                
                for env in env_vars:
                    env_name = env.get("name", "")
                    env_value = env.get("value", "")
                    
                    # Look for service references
                    if "_SERVICE_" in env_name or "_HOST" in env_name or "_ADDR" in env_name:
                        # Extract target service name
                        target = self._extract_service_from_env(env_name, env_value)
                        if target and target != source_name:
                            self.graph.add_edge(DependencyEdge(
                                source_id=source_name,
                                target_id=target,
                                dependency_type=DependencyType.CALLS,
                                protocol=detect_protocol(target),
                            ))
        
        logger.info(f"Built K8s graph: {self.graph.stats()}")
        return self.graph
    
    def _extract_service_from_env(self, env_name: str, env_value: str) -> Optional[str]:
        """Extract service name from environment variable."""
        # Try to extract from env name (e.g., CART_SERVICE_ADDR -> cart)
        patterns = [
            r"^([A-Z]+)_SERVICE",
            r"^([A-Z]+)_HOST",
            r"^([A-Z]+)_ADDR",
        ]
        
        for pattern in patterns:
            match = re.match(pattern, env_name)
            if match:
                return match.group(1).lower()
        
        # Try to extract from value (e.g., cart:8080 -> cart)
        if env_value:
            match = re.match(r"^([a-z][a-z0-9-]+)", env_value.lower())
            if match:
                return match.group(1)
        
        return None
    
    def add_custom_service(
        self,
        service_id: str,
        name: str,
        service_type: str = "backend",
        language: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Manually add a service.
        
        Args:
            service_id: Unique service ID
            name: Display name
            service_type: Type (frontend, backend, database, etc.)
            language: Programming language
            **kwargs: Additional ServiceNode fields
        """
        self.graph.add_node(ServiceNode(
            id=service_id,
            name=name,
            service_type=ServiceType(service_type),
            language=language,
            **kwargs,
        ))
    
    def add_custom_dependency(
        self,
        source_id: str,
        target_id: str,
        dep_type: str = "calls",
        protocol: str = "http",
        is_critical: bool = False,
    ) -> None:
        """Manually add a dependency.
        
        Args:
            source_id: Source service
            target_id: Target service
            dep_type: Dependency type
            protocol: Communication protocol
            is_critical: Whether this is a critical path
        """
        self.graph.add_edge(DependencyEdge(
            source_id=source_id,
            target_id=target_id,
            dependency_type=DependencyType(dep_type),
            protocol=Protocol(protocol),
            is_critical=is_critical,
        ))
    
    def get_graph(self) -> ServiceGraph:
        """Get the built graph."""
        return self.graph


def build_otel_demo_graph() -> ServiceGraph:
    """Convenience function to build OTEL demo graph."""
    builder = GraphBuilder()
    return builder.build_from_otel_demo()
