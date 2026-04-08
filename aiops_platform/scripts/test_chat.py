#!/usr/bin/env python3
"""Test script for AIOps Chat with Ollama LLM.

Usage:
    python scripts/test_chat.py

Requires:
    - Ollama running with gemma3:12b model
    - Knowledge base indexed
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.llm import AIOpsChat


def main():
    print("=" * 60)
    print("AIOps Chat Test - Ollama + HybridRAG")
    print("=" * 60)
    
    # Initialize chat
    print("\n[1/3] Initializing AIOps Chat...")
    chat = AIOpsChat(
        model="gemma3:12b",
        use_rag=True,
        use_graph=True,
    )
    
    # Check Ollama
    if not chat.llm.is_available():
        print("❌ Ollama không khả dụng! Hãy chạy: ollama serve")
        return
    
    print(f"✓ Ollama OK - Model: {chat.llm.model}")
    print(f"  Available models: {chat.llm.list_models()}")
    
    # Setup RAG
    print("\n[2/3] Setting up RAG (indexing knowledge base)...")
    stats = chat.setup_rag(show_progress=False)
    print(f"✓ RAG indexed: {stats.get('chunks_indexed', 0)} chunks, {stats.get('files_processed', 0)} files")
    
    # Test queries
    print("\n[3/3] Testing queries...")
    print("-" * 60)
    
    test_queries = [
        ("incident", "checkout service bị timeout khi thanh toán"),
        ("architecture", "cart service kết nối với những service nào?"),
        ("rca", "Error 500 từ payment service, nguyên nhân có thể là gì?"),
    ]
    
    for query_type, query in test_queries:
        print(f"\n📝 Query ({query_type}): {query}")
        print("-" * 40)
        
        response = chat.ask(query, query_type=query_type)
        
        print(f"📚 Sources: {response.sources[:3]}")
        print(f"🔗 Related services: {response.related_services[:5]}")
        print(f"📖 Context used: {response.context_used}")
        print(f"\n💬 Answer:\n{response.answer[:500]}...")
        print("-" * 60)
    
    # Interactive mode
    print("\n" + "=" * 60)
    print("Interactive Mode (gõ 'quit' để thoát)")
    print("=" * 60)
    
    while True:
        try:
            user_input = input("\n🧑 You: ").strip()
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Bye!")
                break
            
            if not user_input:
                continue
            
            response = chat.ask(user_input)
            print(f"\n🤖 Assistant:\n{response.answer}")
            
            if response.sources:
                print(f"\n📚 Sources: {', '.join(response.sources[:3])}")
            
        except KeyboardInterrupt:
            print("\nBye!")
            break


if __name__ == "__main__":
    main()
