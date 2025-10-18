"""
Perplexity Client
Usa la API compatible con OpenAI en https://api.perplexity.ai
"""

import os
from typing import Dict, Optional
from openai import OpenAI
from src.query_executor.api_clients.base import BaseAIClient


class PerplexityClient(BaseAIClient):
    """Cliente para Perplexity AI (endpoint OpenAI-compatible)."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        api_key = api_key or os.getenv("PPLX_API_KEY")
        model = model or os.getenv("PPLX_MODEL", "sonar-small-online")

        super().__init__(api_key, model)

        # OpenAI SDK apuntando al endpoint de Perplexity
        self.client = OpenAI(api_key=api_key, base_url=os.getenv("PPLX_BASE_URL", "https://api.perplexity.ai"))

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Dict:
        max_tokens = max_tokens or 800

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        usage = response.usage
        return {
            'response_text': response.choices[0].message.content,
            'tokens_input': getattr(usage, 'prompt_tokens', 0),
            'tokens_output': getattr(usage, 'completion_tokens', 0),
            'model': self.model
        }

"""
Perplexity Client
Cliente para Perplexity AI (modelos Sonar con búsqueda online)
"""

import os
import time
from typing import Dict, Optional
import requests

from src.query_executor.api_clients.base import BaseAIClient


class PerplexityClient(BaseAIClient):
    """Cliente para la API de Perplexity (sonar/online)"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Perplexity client
        
        Args:
            api_key: API key (si None, se lee de env PPLX_API_KEY)
            model: Modelo a usar (si None, se lee de env PPLX_MODEL)
        """
        api_key = api_key or os.getenv("PPLX_API_KEY")
        model = model or os.getenv("PPLX_MODEL", "sonar-small-online")

        super().__init__(api_key, model)

        self.base_url = os.getenv("PPLX_BASE_URL", "https://api.perplexity.ai")
        self.timeout_seconds = int(os.getenv("PPLX_TIMEOUT_SECONDS", "60"))

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Dict:
        """
        Genera una respuesta usando Perplexity (Chat Completions compatible)
        """
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload: Dict = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        start = time.time()
        resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout_seconds)
        elapsed_ms = int((time.time() - start) * 1000)

        if resp.status_code >= 400:
            raise RuntimeError(f"Perplexity API error {resp.status_code}: {resp.text}")

        data = resp.json()

        # Campos compatibles con OpenAI-like
        text = ""
        try:
            text = data["choices"][0]["message"]["content"]
        except Exception:
            # Fallback
            text = data.get("output_text", "") or ""

        usage = data.get("usage", {}) or {}
        tokens_input = int(usage.get("prompt_tokens", 0) or 0)
        tokens_output = int(usage.get("completion_tokens", 0) or 0)

        return {
            "response_text": text,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "model": self.model,
            "latency_ms": elapsed_ms,
        }


