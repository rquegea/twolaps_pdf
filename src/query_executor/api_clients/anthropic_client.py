"""
Anthropic Client
Cliente para Anthropic (Claude)
"""

import os
from typing import Dict, Optional
from anthropic import Anthropic
from src.query_executor.api_clients.base import BaseAIClient


class AnthropicClient(BaseAIClient):
    """Cliente para la API de Anthropic (Claude)"""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Anthropic client
        
        Args:
            api_key: API key (si None, se lee de env)
            model: Modelo a usar (si None, se lee de env)
        """
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        model = model or os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        
        super().__init__(api_key, model)
        
        self.client = Anthropic(api_key=api_key)
    
    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Dict:
        """
        Genera una respuesta usando Claude
        
        Args:
            prompt: Texto del prompt
            temperature: Temperatura (0-1)
            max_tokens: Máximo de tokens
        
        Returns:
            Dict con respuesta y métricas
        """
        max_tokens = max_tokens or 4096
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return {
            'response_text': response.content[0].text,
            'tokens_input': response.usage.input_tokens,
            'tokens_output': response.usage.output_tokens,
            'model': self.model
        }

