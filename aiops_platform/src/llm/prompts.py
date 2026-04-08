"""Prompt templates for AIOps chatbot.

RAG Prompting follows proven patterns from:
- OpenAI RAG Best Practices (2023)
- LangChain RAG Documentation
- "Lost in the Middle" paper (Liu et al., 2023) - context placement

Key principles:
1. Context BEFORE question (reduces "lost in the middle" effect)
2. Explicit instruction to use ONLY provided context
3. Clear fallback when context insufficient
"""

# System prompt follows OpenAI's recommended structure for RAG
SYSTEM_PROMPT = """You are an AIOps assistant for Kubernetes incident analysis.

IMPORTANT RULES:
1. Answer ONLY based on the provided context
2. If the context does not contain the answer, say "I don't have this information in my knowledge base"
3. Do not make up information
4. Be concise and specific

System: OpenTelemetry Demo (21 microservices on Kubernetes)"""


class PromptTemplates:
    """RAG prompt templates following proven patterns.
    
    Based on:
    - OpenAI RAG Guide: https://platform.openai.com/docs/guides/prompt-engineering
    - LangChain RAG: https://python.langchain.com/docs/use_cases/question_answering/
    - "Lost in the Middle" (Liu et al., 2023): Place relevant info at start/end
    """
    
    @staticmethod
    def rag_qa(query: str, context: str) -> str:
        """Standard RAG Q&A prompt (OpenAI pattern).
        
        Pattern: Context → Question → Instruction
        This order reduces the "lost in the middle" effect.
        """
        return f"""Answer the question based ONLY on the following context:

<context>
{context}
</context>

Question: {query}

If the context does not contain enough information to answer, say "I don't have this information in my knowledge base."
Answer in the same language as the question."""

    @staticmethod
    def incident_analysis(incident: str, context: str) -> str:
        """Incident analysis prompt."""
        return f"""Based ONLY on the following context, analyze the incident:

<context>
{context}
</context>

Incident: {incident}

Provide:
1. Possible causes (based on context only)
2. Affected services
3. Recommended actions

If context is insufficient, state what additional information is needed."""

    @staticmethod
    def root_cause_analysis(
        incident: str,
        context: str,
        related_services: list,
    ) -> str:
        """RCA prompt with dependency context."""
        services_str = ", ".join(related_services) if related_services else "Unknown"
        
        return f"""Based ONLY on the following context, perform root cause analysis:

<context>
{context}
</context>

Incident: {incident}
Related services (from dependency graph): {services_str}

Analyze:
1. Root cause - which service/component is the source?
2. Impact path - how did the issue propagate?
3. Evidence - what in the context supports your conclusion?
4. Remediation steps

Focus on ROOT cause, not symptoms. If context is insufficient, state what's missing."""

    @staticmethod
    def architecture_query(query: str, context: str) -> str:
        """Architecture/knowledge question prompt."""
        return PromptTemplates.rag_qa(query, context)

    @staticmethod
    def service_troubleshoot(
        service: str,
        symptoms: str,
        context: str,
    ) -> str:
        """Service troubleshooting prompt."""
        return f"""Based ONLY on the following context, troubleshoot the service:

<context>
{context}
</context>

Service: {service}
Symptoms: {symptoms}

Provide:
1. Immediate checks
2. Common causes for these symptoms
3. Debug commands
4. Resolution steps

Use only information from the context."""

    @staticmethod
    def general_chat(query: str, context: str) -> str:
        """General chat with RAG context."""
        if context and context.strip():
            return PromptTemplates.rag_qa(query, context)
        else:
            return f"""Question: {query}

Answer as an AIOps assistant. If you need specific system information, ask for it."""
