"""Neo4j graph store for service dependency graph.

Provides persistent storage and querying of the service graph
using Neo4j database with Cypher queries.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from contextlib import contextmanager

from .schema import (
    ServiceNode, 
    DependencyEdge, 
    ServiceGraph,
    ServiceType,
    DependencyType,
    Protocol,
)

logger = logging.getLogger(__name__)


# Default Neo4j connection settings
DEFAULT_NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
DEFAULT_NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
DEFAULT_NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")


class Neo4jStore:
    """Neo4j graph store for service dependencies."""
    
    def __init__(
        self,
        uri: str = DEFAULT_NEO4J_URI,
        user: str = DEFAULT_NEO4J_USER,
        password: str = DEFAULT_NEO4J_PASSWORD,
    ):
        """Initialize Neo4j connection.
        
        Args:
            uri: Neo4j bolt URI
            user: Database user
            password: Database password
        """
        self.uri = uri
        self.user = user
        self.password = password
        self._driver = None
    
    @property
    def driver(self):
        """Lazy load Neo4j driver."""
        if self._driver is None:
            try:
                from neo4j import GraphDatabase
                self._driver = GraphDatabase.driver(
                    self.uri,
                    auth=(self.user, self.password),
                )
                # Verify connection
                self._driver.verify_connectivity()
                logger.info(f"Connected to Neo4j at {self.uri}")
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j: {e}")
                raise
        return self._driver
    
    def close(self):
        """Close the driver connection."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None
    
    @contextmanager
    def session(self):
        """Get a database session."""
        session = self.driver.session()
        try:
            yield session
        finally:
            session.close()
    
    def init_schema(self):
        """Initialize graph schema with constraints and indexes."""
        with self.session() as session:
            # Create constraint for unique service IDs
            session.run("""
                CREATE CONSTRAINT service_id IF NOT EXISTS
                FOR (s:Service) REQUIRE s.id IS UNIQUE
            """)
            
            # Create index for faster lookups
            session.run("""
                CREATE INDEX service_namespace IF NOT EXISTS
                FOR (s:Service) ON (s.namespace)
            """)
            
            session.run("""
                CREATE INDEX service_type IF NOT EXISTS
                FOR (s:Service) ON (s.service_type)
            """)
            
            logger.info("Neo4j schema initialized")
    
    def clear_graph(self):
        """Delete all nodes and relationships."""
        with self.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            logger.info("Graph cleared")
    
    # ==================== Node Operations ====================
    
    def add_service(self, node: ServiceNode) -> bool:
        """Add or update a service node.
        
        Args:
            node: ServiceNode to add
            
        Returns:
            True if successful
        """
        query = """
            MERGE (s:Service {id: $id})
            SET s.name = $name,
                s.namespace = $namespace,
                s.service_type = $service_type,
                s.language = $language,
                s.image = $image,
                s.replicas = $replicas,
                s.cpu_limit = $cpu_limit,
                s.memory_limit = $memory_limit,
                s.labels = $labels,
                s.annotations = $annotations
            RETURN s
        """
        
        with self.session() as session:
            result = session.run(query, **node.to_dict())
            return result.single() is not None
    
    def get_service(self, service_id: str) -> Optional[ServiceNode]:
        """Get a service by ID.
        
        Args:
            service_id: Service identifier
            
        Returns:
            ServiceNode or None
        """
        query = "MATCH (s:Service {id: $id}) RETURN s"
        
        with self.session() as session:
            result = session.run(query, id=service_id)
            record = result.single()
            
            if record:
                node_data = dict(record["s"])
                return ServiceNode.from_dict(node_data)
            return None
    
    def list_services(self, namespace: Optional[str] = None) -> List[ServiceNode]:
        """List all services.
        
        Args:
            namespace: Optional namespace filter
            
        Returns:
            List of ServiceNode
        """
        if namespace:
            query = "MATCH (s:Service {namespace: $namespace}) RETURN s"
            params = {"namespace": namespace}
        else:
            query = "MATCH (s:Service) RETURN s"
            params = {}
        
        services = []
        with self.session() as session:
            result = session.run(query, **params)
            for record in result:
                node_data = dict(record["s"])
                services.append(ServiceNode.from_dict(node_data))
        
        return services
    
    def delete_service(self, service_id: str) -> bool:
        """Delete a service and its relationships.
        
        Args:
            service_id: Service to delete
            
        Returns:
            True if deleted
        """
        query = "MATCH (s:Service {id: $id}) DETACH DELETE s RETURN count(s) as deleted"
        
        with self.session() as session:
            result = session.run(query, id=service_id)
            record = result.single()
            return record and record["deleted"] > 0
    
    # ==================== Edge Operations ====================
    
    def add_dependency(self, edge: DependencyEdge) -> bool:
        """Add or update a dependency edge.
        
        Args:
            edge: DependencyEdge to add
            
        Returns:
            True if successful
        """
        # Map dependency type to relationship type
        rel_type = edge.dependency_type.value.upper()
        
        query = f"""
            MATCH (source:Service {{id: $source_id}})
            MATCH (target:Service {{id: $target_id}})
            MERGE (source)-[r:{rel_type}]->(target)
            SET r.protocol = $protocol,
                r.endpoint = $endpoint,
                r.is_critical = $is_critical,
                r.latency_p99_ms = $latency_p99_ms,
                r.metadata = $metadata
            RETURN r
        """
        
        with self.session() as session:
            result = session.run(
                query,
                source_id=edge.source_id,
                target_id=edge.target_id,
                protocol=edge.protocol.value,
                endpoint=edge.endpoint,
                is_critical=edge.is_critical,
                latency_p99_ms=edge.latency_p99_ms,
                metadata=json.dumps(edge.metadata),
            )
            return result.single() is not None
    
    def get_dependencies(self, service_id: str, direction: str = "both") -> List[DependencyEdge]:
        """Get dependencies for a service.
        
        Args:
            service_id: Service ID
            direction: 'upstream', 'downstream', or 'both'
            
        Returns:
            List of DependencyEdge
        """
        edges = []
        
        if direction in ("downstream", "both"):
            query = """
                MATCH (s:Service {id: $id})-[r]->(t:Service)
                RETURN s.id as source, t.id as target, type(r) as rel_type, r
            """
            with self.session() as session:
                result = session.run(query, id=service_id)
                for record in result:
                    edge = self._record_to_edge(record)
                    if edge:
                        edges.append(edge)
        
        if direction in ("upstream", "both"):
            query = """
                MATCH (s:Service)-[r]->(t:Service {id: $id})
                RETURN s.id as source, t.id as target, type(r) as rel_type, r
            """
            with self.session() as session:
                result = session.run(query, id=service_id)
                for record in result:
                    edge = self._record_to_edge(record)
                    if edge:
                        edges.append(edge)
        
        return edges
    
    def _record_to_edge(self, record) -> Optional[DependencyEdge]:
        """Convert Neo4j record to DependencyEdge."""
        try:
            rel_data = dict(record["r"])
            return DependencyEdge(
                source_id=record["source"],
                target_id=record["target"],
                dependency_type=DependencyType(record["rel_type"].lower()),
                protocol=Protocol(rel_data.get("protocol", "unknown")),
                endpoint=rel_data.get("endpoint"),
                is_critical=rel_data.get("is_critical", False),
                latency_p99_ms=rel_data.get("latency_p99_ms"),
                metadata=json.loads(rel_data.get("metadata", "{}")),
            )
        except Exception as e:
            logger.warning(f"Failed to parse edge: {e}")
            return None
    
    # ==================== Graph Traversal ====================
    
    def get_k_hop_neighbors(
        self,
        service_id: str,
        k: int = 2,
        direction: str = "both",
    ) -> Dict[str, Set[str]]:
        """Get services within K hops.
        
        Args:
            service_id: Starting service
            k: Number of hops (1, 2, or 3 recommended)
            direction: 'upstream', 'downstream', or 'both'
            
        Returns:
            Dict mapping hop distance to set of service IDs
        """
        neighbors = {i: set() for i in range(1, k + 1)}
        
        # Build direction pattern
        if direction == "downstream":
            rel_pattern = "-[*1..{k}]->"
        elif direction == "upstream":
            rel_pattern = "<-[*1..{k}]-"
        else:
            rel_pattern = "-[*1..{k}]-"
        
        query = f"""
            MATCH path = (start:Service {{id: $id}}){rel_pattern.format(k=k)}(end:Service)
            WHERE start <> end
            RETURN end.id as neighbor_id, length(path) as distance
        """
        
        with self.session() as session:
            result = session.run(query, id=service_id)
            for record in result:
                dist = record["distance"]
                if dist <= k:
                    neighbors[dist].add(record["neighbor_id"])
        
        return neighbors
    
    def get_related_services(
        self,
        service_ids: List[str],
        k: int = 2,
        include_self: bool = True,
    ) -> List[str]:
        """Get all services related to given services within K hops.
        
        Args:
            service_ids: List of service IDs
            k: Number of hops
            include_self: Include input services in result
            
        Returns:
            List of related service IDs
        """
        related = set()
        
        if include_self:
            related.update(service_ids)
        
        for service_id in service_ids:
            neighbors = self.get_k_hop_neighbors(service_id, k)
            for hop_neighbors in neighbors.values():
                related.update(hop_neighbors)
        
        return list(related)
    
    def get_critical_path(self, source_id: str, target_id: str) -> List[str]:
        """Find shortest path between two services.
        
        Args:
            source_id: Starting service
            target_id: Ending service
            
        Returns:
            List of service IDs in path
        """
        query = """
            MATCH path = shortestPath((s:Service {id: $source})-[*]-(t:Service {id: $target}))
            RETURN [n in nodes(path) | n.id] as path
        """
        
        with self.session() as session:
            result = session.run(query, source=source_id, target=target_id)
            record = result.single()
            if record:
                return record["path"]
        return []
    
    # ==================== Bulk Operations ====================
    
    def import_graph(self, graph: ServiceGraph) -> Dict[str, int]:
        """Import a complete service graph.
        
        Args:
            graph: ServiceGraph to import
            
        Returns:
            Stats about imported nodes and edges
        """
        nodes_added = 0
        edges_added = 0
        
        # Add all nodes first
        for node in graph.nodes:
            if self.add_service(node):
                nodes_added += 1
        
        # Then add edges
        for edge in graph.edges:
            if self.add_dependency(edge):
                edges_added += 1
        
        logger.info(f"Imported {nodes_added} nodes and {edges_added} edges")
        
        return {
            "nodes_added": nodes_added,
            "edges_added": edges_added,
        }
    
    def export_graph(self) -> ServiceGraph:
        """Export the complete graph.
        
        Returns:
            ServiceGraph with all nodes and edges
        """
        graph = ServiceGraph(source="neo4j")
        
        # Get all nodes
        for node in self.list_services():
            graph.add_node(node)
        
        # Get all edges
        query = """
            MATCH (s:Service)-[r]->(t:Service)
            RETURN s.id as source, t.id as target, type(r) as rel_type, r
        """
        
        with self.session() as session:
            result = session.run(query)
            for record in result:
                edge = self._record_to_edge(record)
                if edge:
                    graph.add_edge(edge)
        
        return graph
    
    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics.
        
        Returns:
            Dict with node count, edge count, etc.
        """
        query = """
            MATCH (s:Service)
            OPTIONAL MATCH (s)-[r]->()
            RETURN 
                count(DISTINCT s) as node_count,
                count(r) as edge_count,
                collect(DISTINCT s.namespace) as namespaces,
                collect(DISTINCT s.service_type) as service_types
        """
        
        with self.session() as session:
            result = session.run(query)
            record = result.single()
            
            if record:
                return {
                    "node_count": record["node_count"],
                    "edge_count": record["edge_count"],
                    "namespaces": record["namespaces"],
                    "service_types": record["service_types"],
                }
        
        return {"node_count": 0, "edge_count": 0}


# ==================== Fallback JSON Store ====================

class JsonGraphStore:
    """Simple JSON-based graph store for development/testing.
    
    Use when Neo4j is not available.
    """
    
    def __init__(self, file_path: Optional[Path] = None):
        """Initialize JSON store.
        
        Args:
            file_path: Path to JSON file (default: data/graph/service_graph.json)
        """
        if file_path is None:
            from ..retrieval.config import PROJECT_ROOT
            file_path = PROJECT_ROOT / "data" / "graph" / "service_graph.json"
        
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._graph: Optional[ServiceGraph] = None
    
    @property
    def graph(self) -> ServiceGraph:
        """Load or create graph."""
        if self._graph is None:
            self._graph = self._load()
        return self._graph
    
    def _load(self) -> ServiceGraph:
        """Load graph from file."""
        if self.file_path.exists():
            with open(self.file_path) as f:
                data = json.load(f)
                return ServiceGraph.from_dict(data)
        return ServiceGraph()
    
    def _save(self):
        """Save graph to file."""
        with open(self.file_path, "w") as f:
            json.dump(self.graph.to_dict(), f, indent=2)
    
    def add_service(self, node: ServiceNode) -> bool:
        """Add a service node."""
        self.graph.add_node(node)
        self._save()
        return True
    
    def get_service(self, service_id: str) -> Optional[ServiceNode]:
        """Get service by ID."""
        return self.graph.get_node(service_id)
    
    def list_services(self, namespace: Optional[str] = None) -> List[ServiceNode]:
        """List services."""
        if namespace:
            return [n for n in self.graph.nodes if n.namespace == namespace]
        return self.graph.nodes
    
    def add_dependency(self, edge: DependencyEdge) -> bool:
        """Add dependency edge."""
        self.graph.add_edge(edge)
        self._save()
        return True
    
    def get_k_hop_neighbors(
        self,
        service_id: str,
        k: int = 2,
        direction: str = "both",
    ) -> Dict[str, Set[str]]:
        """Get K-hop neighbors using BFS."""
        neighbors = {i: set() for i in range(1, k + 1)}
        visited = {service_id}
        current_level = {service_id}
        
        for hop in range(1, k + 1):
            next_level = set()
            
            for sid in current_level:
                node_neighbors = self.graph.get_neighbors(sid, direction)
                for neighbor in node_neighbors:
                    if neighbor not in visited:
                        neighbors[hop].add(neighbor)
                        next_level.add(neighbor)
                        visited.add(neighbor)
            
            current_level = next_level
            if not current_level:
                break
        
        return neighbors
    
    def get_related_services(
        self,
        service_ids: List[str],
        k: int = 2,
        include_self: bool = True,
    ) -> List[str]:
        """Get related services within K hops."""
        related = set()
        
        if include_self:
            related.update(service_ids)
        
        for service_id in service_ids:
            neighbors = self.get_k_hop_neighbors(service_id, k)
            for hop_neighbors in neighbors.values():
                related.update(hop_neighbors)
        
        return list(related)
    
    def import_graph(self, graph: ServiceGraph) -> Dict[str, int]:
        """Import graph."""
        for node in graph.nodes:
            self.graph.add_node(node)
        for edge in graph.edges:
            self.graph.add_edge(edge)
        self._save()
        return {
            "nodes_added": len(graph.nodes),
            "edges_added": len(graph.edges),
        }
    
    def export_graph(self) -> ServiceGraph:
        """Export graph."""
        return self.graph
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return self.graph.stats()
    
    def clear_graph(self):
        """Clear the graph."""
        self._graph = ServiceGraph()
        self._save()


def get_graph_store(use_neo4j: bool = True, **kwargs) -> "Neo4jStore | JsonGraphStore":
    """Factory function to get appropriate graph store.
    
    Args:
        use_neo4j: Whether to use Neo4j (falls back to JSON if unavailable)
        **kwargs: Arguments for store initialization
        
    Returns:
        Graph store instance
    """
    if use_neo4j:
        try:
            store = Neo4jStore(**kwargs)
            store.driver  # Test connection
            return store
        except Exception as e:
            logger.warning(f"Neo4j unavailable ({e}), falling back to JSON store")
    
    return JsonGraphStore(**kwargs)
