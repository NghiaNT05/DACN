#!/usr/bin/env python3
"""Simple interactive chat - skips test queries."""

import sys
import logging
import warnings
from pathlib import Path

# Suppress warnings and debug logs
warnings.filterwarnings("ignore")
logging.getLogger().setLevel(logging.ERROR)

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.llm import AIOpsChat

def main():
    print("🤖 AIOps Chat - Initializing...")
    
    chat = AIOpsChat(model="gemma3:12b", use_rag=True, use_graph=True)
    
    if not chat.llm.is_available():
        print("❌ Ollama không khả dụng!")
        return
    
    print("📚 Indexing knowledge base...")
    stats = chat.setup_rag(show_progress=False)
    print(f"✓ Indexed {stats.get('chunks_indexed', 0)} chunks")
    
    print("\n" + "="*50)
    print("Interactive Mode - gõ 'quit' để thoát")
    print("="*50 + "\n")
    
    while True:
        try:
            user_input = input("🧑 You: ").strip()
            if user_input.lower() in ["quit", "exit", "q"]:
                break
            if not user_input:
                continue
            
            print("🤔 Thinking...")
            response = chat.ask(user_input)
            print(f"\n🤖 Assistant:\n{response.answer}\n")
            
            if response.sources:
                print(f"📚 Sources: {', '.join(Path(s).name for s in response.sources[:3])}\n")
                
        except KeyboardInterrupt:
            break
    
    print("Bye!")

if __name__ == "__main__":
    main()
