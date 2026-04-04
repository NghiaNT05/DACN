"""Graph schema definitions for service dependency graph.

Defines the structure of nodes (services) and edges (dependencies)
used in GraphRAG for incident analysis.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime


class ServiceType(Enum):
    """Types of services in the graph."""
    FRONTEND = "frontend"
    BACKEND = "backend"
    DATABASE = "database"
    CACHE = "cache"
    QUEUE = "queue"
    GATEWAY = "gateway"
    WORKER = "worker"
    EXTERNAL = "external"


class DependencyType(Enum):
    """Types of dependencies between services."""
    CALLS = "calls"              # Synchronous HTTP/gRPC call
    PUBLISHES_TO = "publishes_to"  # Async message publishing
    CONSUMES_FROM = "consumes_from"  # Async message consuming
    CONSUMES = "consumes"        # Alias for consumes_from
    READS_FROM = "reads_from"    # Database/cache read
    WRITES_TO = "writes_to"      # Database/cache write
    USES = "uses"                # Generic usage (e.g., Redis, DB)
    DEPENDS_ON = "depends_on"    # Generic dependency
    EXPORTS = "exports"          # Telemetry export
    PROXIES = "proxies"          # Proxy/gateway


class Protocol(Enum):
    """Communication protocols."""
    HTTP = "http"
    GRPC = "grpc"
    KAFKA = "kafka"
    REDIS = "redis"
    POSTGRES = "postgres"
    MONGODB = "mongodb"
    TCP = "tcp"
    UNKNOWN = "unknown"


@dataclass
class ServiceNode:
    """A service node in the dependency graph."""
    
    id: str                          # Unique identifier (e.g., "checkout")
    name: str                        # Display name
    namespace: str = "default"       # Kubernetes namespace
    service_type: ServiceType = ServiceType.BACKEND
    
    # Technical details
    language: Optional[str] = None   # go, python, java, etc.
    image: Optional[str] = None      # Container image
    replicas: int = 1
    
    # Resource info
    cpu_limit: Optional[str] = None
    memory_limit: Optional[str] = None
    
    # Metadata
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Neo4j."""
        return {
            "id": self.id,
            "name": self.name,
            "namespace": self.namespace,
            "service_type": self.service_type.value,
            "language": self.language,
            "image": self.image,
            "replicas": self.replicas,
            "cpu_limit": self.cpu_limit,
            "memory_limit": self.memory_limit,
            "labels": self.labels,
            "annotations": self.annotations,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServiceNode":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            namespace=data.get("namespace", "default"),
            service_type=ServiceType(data.get("service_type", "backend")),
            language=data.get("language"),
            image=data.get("image"),
            replicas=data.get("replicas", 1),
            cpu_limit=data.get("cpu_limit"),
            memory_limit=data.get("memory_limit"),
            labels=data.get("labels", {}),
            annotations=data.get("annotations", {}),
        )


@dataclass
class DependencyEdge:
    """A dependency edge between services."""
    
    source_id: str                   # Source service ID
    target_id: str                   # Target service ID
    dependency_type: DependencyType = DependencyType.CALLS
    protocol: Protocol = Protocol.HTTP
    
    # Edge properties
    endpoint: Optional[str] = None   # API endpoint or topic name
    is_critical: bool = False        # Critical path dependency
    latency_p99_ms: Optional[float] = None  # Expected latency
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Neo4j."""
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "dependency_type": self.dependency_type.value,
            "protocol": self.protocol.value,
            "endpoint": self.endpoint,
            "is_critical": self.is_critical,
            "latency_p99_ms": self.latency_p99_ms,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DependencyEdge":
        """Create from dictionary."""
        return cls(
            source_id=data["source_id"],
            target_id=data["target_id"],
            dependency_type=DependencyType(data.get("dependency_type", "calls")),
            protocol=Protocol(data.get("protocol", "unknown")),
            endpoint=data.get("endpoint"),
            is_critical=data.get("is_critical", False),
            latency_p99_ms=data.get("latency_p99_ms"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ServiceGraph:
    """Complete service dependency graph."""
    
    nodes: List[ServiceNode] = field(default_factory=list)
    edges: List[DependencyEdge] = field(default_factory=list)
    
    # Graph metadata
    name: str = "service_graph"
    version: str = "1.0"
    source: str = "kubernetes"  # kubernetes, opentelemetry, manual
    
    def add_node(self, node: ServiceNode) -> None:
        """Add a service node."""
        # Check for duplicates
        if not any(n.id == node.id for n in self.nodes):
            self.nodes.append(node)
    
    def add_edge(self, edge: DependencyEdge) -> None:
        """Add a dependency edge."""
        # Check for duplicates
        existing = any(
            e.source_id == edge.source_id and 
            e.target_id == edge.target_id and
            e.dependency_type == edge.dependency_type
            for e in self.edges
        )
        if not existing:
            self.edges.append(edge)
    
    def get_node(self, node_id: str) -> Optional[ServiceNode]:
        """Get a node by ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None
    
    def get_upstream(self, node_id: str) -> List[str]:
        """Get services that call this service (upstream)."""
        return [e.source_id for e in self.edges if e.target_id == node_id]
    
    def get_downstream(self, node_id: str) -> List[str]:
        """Get services that this service calls (downstream)."""
        return [e.target_id for e in self.edges if e.source_id == node_id]
    
    def get_neighbors(self, node_id: str, direction: str = "both") -> List[str]:
        """Get neighboring services.
        
        Args:
            node_id: Service ID
            direction: 'upstream', 'downstream', or 'both'
        """
        neighbors = set()
        
        if direction in ("upstream", "both"):
            neighbors.update(self.get_upstream(node_id))
        
        if direction in ("downstream", "both"):
            neighbors.update(self.get_downstream(node_id))
        
        return list(neighbors)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "source": self.source,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServiceGraph":
        """Create from dictionary."""
        graph = cls(
            name=data.get("name", "service_graph"),
            version=data.get("version", "1.0"),
            source=data.get("source", "unknown"),
        )
        
        for node_data in data.get("nodes", []):
            graph.add_node(ServiceNode.from_dict(node_data))
        
        for edge_data in data.get("edges", []):
            graph.add_edge(DependencyEdge.from_dict(edge_data))
        
        return graph
    
    def stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "avg_connections": len(self.edges) / len(self.nodes) if self.nodes else 0,
            "namespaces": list(set(n.namespace for n in self.nodes)),
            "service_types": list(set(n.service_type.value for n in self.nodes)),
        }
