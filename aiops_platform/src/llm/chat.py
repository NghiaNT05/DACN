"""AIOps Chat - Main chat interface combining RAG + LLM.

Integrates HybridRAG retrieval with Ollama LLM for incident analysis.
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from .client import OllamaClient, DEFAULT_MODEL
from .prompts import PromptTemplates, SYSTEM_PROMPT

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    """A single chat message."""
    role: str  # "user", "assistant", "system"
    content: str
    
    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


@dataclass 
class ChatResponse:
    """Response from AIOps chat."""
    answer: str
    sources: List[str] = field(default_factory=list)
    related_services: List[str] = field(default_factory=list)
    context_used: bool = False
    
    def to_dict(self) -> dict:
        return {
            "answer": self.answer,
            "sources": self.sources,
            "related_services": self.related_services,
            "context_used": self.context_used,
        }


class AIOpsChat:
    """AIOps chatbot combining HybridRAG + LLM.
    
    Usage:
        chat = AIOpsChat()
        chat.setup_rag()  # Index knowledge base
        response = chat.ask("checkout service bị timeout")
    """
    
    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        ollama_url: str = "http://localhost:11434",
        use_rag: bool = True,
        use_graph: bool = True,
    ):
        """Initialize AIOps chat.
        
        Args:
            model: Ollama model name
            ollama_url: Ollama server URL
            use_rag: Enable RAG retrieval
            use_graph: Enable GraphRAG (K-hop expansion)
        """
        self.llm = OllamaClient(base_url=ollama_url, model=model)
        self.use_rag = use_rag
        self.use_graph = use_graph
        
        self.hybrid_rag = None
        self.vector_retriever = None
        
        self.history: List[ChatMessage] = []
        self.max_history = 10
    
    def setup_rag(
        self,
        knowledge_dir: Optional[str] = None,
        show_progress: bool = True,
    ) -> Dict[str, Any]:
        """Setup and index knowledge base for RAG.
        
        Args:
            knowledge_dir: Path to knowledge directory
            show_progress: Show indexing progress
            
        Returns:
            Indexing statistics
        """
        from src.retrieval.retriever import HybridRetriever
        from src.graph.fusion import HybridRAGFusion
        from src.graph.retriever import GraphRetriever
        
        # Setup vector retriever
        self.vector_retriever = HybridRetriever(use_reranker=True)
        
        # Index knowledge base
        stats = self.vector_retriever.index_knowledge_base(
            show_progress=show_progress,
        )
        
        # Setup HybridRAG if graph enabled
        if self.use_graph:
            graph_retriever = GraphRetriever(k_hop=2)
            self.hybrid_rag = HybridRAGFusion(
                vector_retriever=self.vector_retriever,
                graph_retriever=graph_retriever,
            )
        
        logger.info(f"RAG setup complete: {stats}")
        return stats
    
    def ask(
        self,
        question: str,
        query_type: str = "auto",
        temperature: float = 0.7,
        include_history: bool = True,
    ) -> ChatResponse:
        """Ask a question.
        
        Args:
            question: User question
            query_type: "incident", "rca", "architecture", "service", "auto"
            temperature: LLM temperature
            include_history: Include chat history
            
        Returns:
            ChatResponse with answer and sources
        """
        # Check LLM availability
        if not self.llm.is_available():
            return ChatResponse(
                answer="❌ Không thể kết nối Ollama. Hãy đảm bảo Ollama đang chạy.",
                context_used=False,
            )
        
        # Retrieve context if RAG is enabled
        context = ""
        sources = []
        related_services = []
        
        if self.use_rag and self.vector_retriever:
            context, sources, related_services = self._retrieve_context(question)
        
        # Build prompt based on query type
        prompt = self._build_prompt(
            question=question,
            context=context,
            query_type=query_type,
            related_services=related_services,
        )
        
        # Build messages with history
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        if include_history:
            for msg in self.history[-self.max_history:]:
                messages.append(msg.to_dict())
        
        messages.append({"role": "user", "content": prompt})
        
        # Generate response
        try:
            answer = self.llm.chat(
                messages=messages,
                temperature=temperature,
            )
        except Exception as e:
            logger.error(f"LLM error: {e}")
            answer = f"❌ Lỗi khi gọi LLM: {e}"
        
        # Update history
        self.history.append(ChatMessage(role="user", content=question))
        self.history.append(ChatMessage(role="assistant", content=answer))
        
        return ChatResponse(
            answer=answer,
            sources=sources,
            related_services=related_services,
            context_used=bool(context),
        )
    
    def analyze_incident(
        self,
        incident_description: str,
        do_rca: bool = True,
    ) -> ChatResponse:
        """Analyze an incident.
        
        Args:
            incident_description: Description of the incident
            do_rca: Perform root cause analysis
            
        Returns:
            ChatResponse with analysis
        """
        query_type = "rca" if do_rca else "incident"
        return self.ask(
            question=incident_description,
            query_type=query_type,
            temperature=0.5,  # Lower for more focused analysis
        )
    
    def troubleshoot_service(
        self,
        service: str,
        symptoms: str,
    ) -> ChatResponse:
        """Troubleshoot a specific service.
        
        Args:
            service: Service name
            symptoms: Observed symptoms
            
        Returns:
            ChatResponse with troubleshooting steps
        """
        question = f"Service: {service}\nSymptoms: {symptoms}"
        return self.ask(
            question=question,
            query_type="service",
            temperature=0.5,
        )
    
    def _retrieve_context(self, query: str) -> tuple:
        """Retrieve context using RAG with query preprocessing.
        
        Uses query expansion (LangChain pattern) to improve retrieval
        for multilingual queries.
        
        Returns:
            (context_text, sources, related_services)
        """
        from src.retrieval.query import preprocess_query
        
        # Preprocess query (expand Vietnamese to English keywords)
        processed = preprocess_query(query)
        search_query = processed["expanded"]
        
        sources = []
        related_services = processed["services"]  # Services from query
        
        if self.use_graph and self.hybrid_rag:
            # Use HybridRAG with expanded query
            result = self.hybrid_rag.search(search_query, top_k=5)
            context = result.get_combined_context(max_chunks=5)
            sources = result.get_sources()
            # Add graph-discovered services
            related_services.extend(result.graph_context.get_all_services())
            related_services = list(set(related_services))
        elif self.vector_retriever:
            # Use vector-only RAG
            result = self.vector_retriever.search(search_query, top_k=5)
            context = result.get_context(max_chunks=5)
            sources = result.get_sources()
        else:
            context = ""
        
        return context, sources, related_services
    
    def _build_prompt(
        self,
        question: str,
        context: str,
        query_type: str,
        related_services: list,
    ) -> str:
        """Build RAG prompt following proven patterns.
        
        Uses standard RAG Q&A format by default.
        Based on OpenAI RAG Guide and LangChain patterns.
        """
        # Use standard RAG Q&A for most queries
        # Only use specialized prompts for explicit incident/RCA analysis
        if query_type == "auto":
            query_type = self._detect_query_type(question)
        
        if query_type == "incident":
            return PromptTemplates.incident_analysis(question, context)
        elif query_type == "rca":
            return PromptTemplates.root_cause_analysis(
                question, context, related_services
            )
        elif query_type == "service":
            service = self._extract_service_name(question)
            return PromptTemplates.service_troubleshoot(
                service, question, context
            )
        else:
            # Default: Standard RAG Q&A (proven pattern)
            return PromptTemplates.rag_qa(question, context)
    
    def _detect_query_type(self, question: str) -> str:
        """Detect query type - conservative approach.
        
        Only classify as incident/rca when keywords are explicit.
        Default to general Q&A (uses standard RAG pattern).
        """
        q_lower = question.lower()
        
        # RCA keywords - explicit analysis requests
        rca_keywords = [
            "root cause", "rca", "nguyên nhân gốc",
            "tại sao lỗi", "why error", "investigate",
        ]
        
        # Incident keywords - explicit incident reports
        incident_keywords = [
            "sự cố", "incident", "outage", "down",
            "error 500", "error 503", "crash",
        ]
        
        if any(kw in q_lower for kw in rca_keywords):
            return "rca"
        elif any(kw in q_lower for kw in incident_keywords):
            return "incident"
        else:
            # Default: general Q&A with RAG
            return "general"
    
    def _extract_service_name(self, question: str) -> str:
        """Extract service name from question."""
        # Common service names in OpenTelemetry Demo
        services = [
            "frontend", "checkout", "cart", "payment", "email",
            "shipping", "product-catalog", "currency", "recommendation",
            "ad", "quote", "kafka", "valkey", "loadgenerator",
        ]
        
        q_lower = question.lower()
        for svc in services:
            if svc in q_lower:
                return svc
        
        return "unknown"
    
    def clear_history(self):
        """Clear chat history."""
        self.history = []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get chat statistics."""
        stats = {
            "model": self.llm.model,
            "history_size": len(self.history),
            "rag_enabled": self.use_rag,
            "graph_enabled": self.use_graph,
        }
        
        if self.vector_retriever:
            stats["retriever"] = self.vector_retriever.get_stats()
        
        if self.hybrid_rag:
            stats["hybrid_rag"] = self.hybrid_rag.get_stats()
        
        return stats
