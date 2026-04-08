"""Query preprocessing for better retrieval.

Techniques based on:
- LangChain Query Transformations
- "Query Expansion" paper patterns

Key techniques:
1. Query expansion - add synonyms/related terms
2. Language detection - handle multilingual queries
"""

import re
from typing import List, Optional

# Vietnamese to English keyword mappings for common terms
VI_EN_KEYWORDS = {
    "viết bằng": "language written in",
    "ngôn ngữ": "language programming",
    "liệt kê": "list all",
    "tất cả": "all",
    "service": "service microservice",
    "dịch vụ": "service microservice",
    "kết nối": "connect dependency",
    "phụ thuộc": "dependency depends on",
    "lỗi": "error failure",
    "sự cố": "incident error",
    "timeout": "timeout latency slow",
    "chậm": "slow latency",
    "kiến trúc": "architecture overview",
}


def expand_query(query: str) -> str:
    """Expand query with related terms for better retrieval.
    
    Based on LangChain's query expansion pattern.
    Helps bridge Vietnamese queries to English knowledge base.
    
    Args:
        query: Original query
        
    Returns:
        Expanded query with additional keywords
    """
    expanded = query
    query_lower = query.lower()
    
    # Add English equivalents for Vietnamese terms
    additions = []
    for vi_term, en_terms in VI_EN_KEYWORDS.items():
        if vi_term in query_lower:
            additions.append(en_terms)
    
    if additions:
        expanded = f"{query} {' '.join(additions)}"
    
    return expanded


def extract_service_names(query: str) -> List[str]:
    """Extract service names mentioned in query.
    
    Args:
        query: User query
        
    Returns:
        List of service names found
    """
    # OpenTelemetry Demo services
    services = [
        "frontend", "checkout", "cart", "payment", "email",
        "shipping", "product-catalog", "productcatalog", "currency",
        "recommendation", "ad", "quote", "kafka", "valkey",
        "load-generator", "loadgenerator", "flagd", "otelcol",
        "jaeger", "prometheus", "grafana", "opensearch",
        "fraud-detection", "frauddetection", "accounting",
        "postgresql", "image-provider",
    ]
    
    query_lower = query.lower()
    found = []
    
    for svc in services:
        if svc in query_lower or svc.replace("-", "") in query_lower:
            # Normalize name
            normalized = svc.replace("-", "")
            if normalized not in [s.replace("-", "") for s in found]:
                found.append(svc)
    
    return found


def preprocess_query(query: str) -> dict:
    """Preprocess query for retrieval.
    
    Returns:
        dict with:
        - original: original query
        - expanded: expanded query for search
        - services: detected service names
    """
    return {
        "original": query,
        "expanded": expand_query(query),
        "services": extract_service_names(query),
    }
