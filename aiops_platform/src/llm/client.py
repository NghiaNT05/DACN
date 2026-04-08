"""Ollama LLM client.

Handles communication with local Ollama server.
"""

import requests
import json
import logging
from typing import Optional, Dict, Any, Generator

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "gemma3:12b"


class OllamaClient:
    """Client for Ollama LLM API."""
    
    def __init__(
        self,
        base_url: str = DEFAULT_OLLAMA_URL,
        model: str = DEFAULT_MODEL,
        timeout: int = 120,
    ):
        """Initialize Ollama client.
        
        Args:
            base_url: Ollama server URL
            model: Model name to use
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout or 300  # 5 minutes for large models
    
    def is_available(self) -> bool:
        """Check if Ollama server is available."""
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5,
            )
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def list_models(self) -> list:
        """List available models."""
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
            return []
        except requests.RequestException as e:
            logger.error(f"Failed to list models: {e}")
            return []
    
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
    ) -> str:
        """Generate text completion.
        
        Args:
            prompt: User prompt
            system: System prompt
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream response
            
        Returns:
            Generated text
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        
        if system:
            payload["system"] = system
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            
            if stream:
                return self._handle_stream(response)
            
            data = response.json()
            return data.get("response", "")
            
        except requests.RequestException as e:
            logger.error(f"Ollama generate failed: {e}")
            raise
    
    def chat(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
    ) -> str:
        """Chat completion with message history.
        
        Args:
            messages: List of {"role": "user/assistant/system", "content": "..."}
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            stream: Whether to stream
            
        Returns:
            Assistant response
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            
            if stream:
                return self._handle_chat_stream(response)
            
            data = response.json()
            return data.get("message", {}).get("content", "")
            
        except requests.RequestException as e:
            logger.error(f"Ollama chat failed: {e}")
            raise
    
    def _handle_stream(self, response) -> str:
        """Handle streaming response."""
        full_response = []
        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                chunk = data.get("response", "")
                full_response.append(chunk)
                if data.get("done"):
                    break
        return "".join(full_response)
    
    def _handle_chat_stream(self, response) -> str:
        """Handle streaming chat response."""
        full_response = []
        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                chunk = data.get("message", {}).get("content", "")
                full_response.append(chunk)
                if data.get("done"):
                    break
        return "".join(full_response)
    
    def stream_generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> Generator[str, None, None]:
        """Stream text generation token by token.
        
        Yields:
            Generated text chunks
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        
        if system:
            payload["system"] = system
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
                stream=True,
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    chunk = data.get("response", "")
                    if chunk:
                        yield chunk
                    if data.get("done"):
                        break
                        
        except requests.RequestException as e:
            logger.error(f"Ollama stream failed: {e}")
            raise
