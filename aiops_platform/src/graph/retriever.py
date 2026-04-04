"""Graph-enhanced retrieval for incident analysis.

Expands search to include related services based on
the service dependency graph (K-hop neighborhood).
"""

import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass

from .schema import ServiceGraph
from .store import Neo4jStore, JsonGraphStore, get_graph_store

logger = logging.getLogger(__name__)


# Default K-hop configuration
# 2-hop is optimal for incident analysis:
# - 1-hop: Only direct dependencies (may miss root cause)
# - 2-hop: Includes dependencies of dependencies (good for cascading failures)
# - 3-hop: Too broad, includes too much noise
DEFAULT_K_HOP = 2


@dataclass
class GraphContext:
    """Context from graph expansion."""
    
    incident_services: List[str]      # Services mentioned in incident
    related_services: List[str]       # Services found via graph traversal
    hop_details: Dict[int, List[str]] # Services by hop distance
    total_services: int               # Total unique services
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_services": self.incident_services,
            "related_services": self.related_services,
            "hop_details": self.hop_details,
            "total_services": self.total_services,
        }
    
    def get_all_services(self) -> List[str]:
        """Get all services (incident + related)."""
        all_services = set(self.incident_services)
        all_services.update(self.related_services)
        return list(all_services)
    
    def get_service_weights(self) -> Dict[str, float]:
        """Get weight for each service based on hop distance.
        
        Closer services get higher weights.
        """
        weights = {}
        
        # Incident services get weight 1.0
        for service in self.incident_services:
            weights[service] = 1.0
        
        # Related services get decaying weights based on hop
        for hop, services in self.hop_details.items():
            weight = 1.0 / (hop + 1)  # 1-hop: 0.5, 2-hop: 0.33, etc.
            for service in services:
                if service not in weights:
                    weights[service] = weight
        
        return weights


class GraphRetriever:
    """Retriever that uses service graph for context expansion."""
    
    def __init__(
        self,
        graph_store: Optional["Neo4jStore | JsonGraphStore"] = None,
        k_hop: int = DEFAULT_K_HOP,
    ):
        """Initialize graph retriever.
        
        Args:
            graph_store: Graph store instance (auto-creates if None)
            k_hop: Default hop distance for expansion
        """
        self.graph_store = graph_store
        self.k_hop = k_hop
        self._initialized = False
    
    def _ensure_store(self):
        """Ensure graph store is initialized."""
        if self.graph_store is None:
            # Try Neo4j, fall back to JSON
            self.graph_store = get_graph_store(use_neo4j=True)
            self._initialized = True
    
    def extract_services_from_text(self, text: str) -> List[str]:
        """Extract service names from incident text.
        
        Args:
            text: Incident description or alert text
            
        Returns:
            List of service IDs found in text
        """
        self._ensure_store()
        
        text_lower = text.lower()
        found_services = []
        
        # Get all known services
        known_services = self.graph_store.list_services()
        
        # Check if any service name appears in text
        for service in known_services:
            # Check both ID and name
            if service.id.lower() in text_lower or service.name.lower() in text_lower:
                found_services.append(service.id)
        
        return list(set(found_services))
    
    def expand_services(
        self,
        service_ids: List[str],
        k: Optional[int] = None,
        direction: str = "both",
    ) -> GraphContext:
        """Expand service list to include related services.
        
        Args:
            service_ids: Starting service IDs
            k: Number of hops (default: self.k_hop)
            direction: 'upstream', 'downstream', or 'both'
            
        Returns:
            GraphContext with expanded service list
        """
        self._ensure_store()
        
        k = k or self.k_hop
        hop_details = {i: [] for i in range(1, k + 1)}
        all_related = set()
        
        for service_id in service_ids:
            neighbors = self.graph_store.get_k_hop_neighbors(
                service_id, k=k, direction=direction
            )
            
            for hop, services in neighbors.items():
                hop_details[hop].extend(services)
                all_related.update(services)
        
        # Remove input services from related
        all_related -= set(service_ids)
        
        # Deduplicate hop_details
        for hop in hop_details:
            hop_details[hop] = list(set(hop_details[hop]) - set(service_ids))
        
        return GraphContext(
            incident_services=service_ids,
            related_services=list(all_related),
            hop_details=hop_details,
            total_services=len(service_ids) + len(all_related),
        )
    
    def get_context_for_incident(
        self,
        incident_text: str,
        k: Optional[int] = None,
    ) -> GraphContext:
        """Get graph context for an incident.
        
        Args:
            incident_text: Incident description
            k: Number of hops
            
        Returns:
            GraphContext with services and relationships
        """
        # Extract services from text
        services = self.extract_services_from_text(incident_text)
        
        if not services:
            logger.warning("No services found in incident text")
            return GraphContext(
                incident_services=[],
                related_services=[],
                hop_details={},
                total_services=0,
            )
        
        # Expand to related services
        return self.expand_services(services, k=k)
    
    def get_service_info(self, service_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed info about a service.
        
        Args:
            service_id: Service ID
            
        Returns:
            Service info dict or None
        """
        self._ensure_store()
        
        service = self.graph_store.get_service(service_id)
        if service:
            return service.to_dict()
        return None
    
    def get_upstream_services(self, service_id: str, k: int = 1) -> List[str]:
        """Get services that depend on this service (callers).
        
        Useful for understanding impact of an incident.
        """
        context = self.expand_services([service_id], k=k, direction="upstream")
        return context.related_services
    
    def get_downstream_services(self, service_id: str, k: int = 1) -> List[str]:
        """Get services this service depends on (callees).
        
        Useful for finding root cause.
        """
        context = self.expand_services([service_id], k=k, direction="downstream")
        return context.related_services
    
    def get_critical_services(self, service_ids: List[str]) -> List[str]:
        """Get services on critical paths involving given services.
        
        Args:
            service_ids: Services to analyze
            
        Returns:
            Services on critical paths
        """
        self._ensure_store()
        
        # For now, return services with is_critical edges
        # A more sophisticated implementation would analyze the graph
        critical = set()
        
        for service_id in service_ids:
            edges = self.graph_store.get_dependencies(service_id)
            for edge in edges:
                if edge.is_critical:
                    critical.add(edge.source_id)
                    critical.add(edge.target_id)
        
        return list(critical)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        self._ensure_store()
        return self.graph_store.get_stats()


def expand_incident_context(
    incident_text: str,
    k_hop: int = DEFAULT_K_HOP,
) -> GraphContext:
    """Convenience function to expand incident context.
    
    Args:
        incident_text: Incident description
        k_hop: Number of hops
        
    Returns:
        GraphContext
    """
    retriever = GraphRetriever(k_hop=k_hop)
    return retriever.get_context_for_incident(incident_text)
