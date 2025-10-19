"""
OpenAI Client
Cliente para OpenAI (GPT-4, GPT-4o, etc.)
"""

import os
from typing import Dict, Optional
from openai import OpenAI
from src.query_executor.api_clients.base import BaseAIClient


class OpenAIClient(BaseAIClient):
    """Cliente para la API de OpenAI"""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize OpenAI client
        
        Args:
            api_key: API key (si None, se lee de env)
            model: Modelo a usar (si None, se lee de env)
        """
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        model = model or os.getenv("OPENAI_MODEL", "gpt-4o")
        
        super().__init__(api_key, model)
        
        self.client = OpenAI(api_key=api_key)
    
    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        json_mode: bool = False
    ) -> Dict:
        """
        Genera una respuesta usando OpenAI
        
        Args:
            prompt: Texto del prompt
            temperature: Temperatura (0-2)
            max_tokens: Máximo de tokens
            json_mode: Si True, fuerza respuesta en formato JSON
        
        Returns:
            Dict con respuesta y métricas
        """
        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature
        }
        
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        
        # Activar JSON mode si se solicita y el modelo lo soporta
        if json_mode and self.model in ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]:
            kwargs["response_format"] = {"type": "json_object"}
        
        response = self.client.chat.completions.create(**kwargs)
        
        return {
            'response_text': response.choices[0].message.content,
            'tokens_input': response.usage.prompt_tokens,
            'tokens_output': response.usage.completion_tokens,
            'model': self.model
        }
    
    def generate_embedding(self, text: str, model: Optional[str] = None) -> list:
        """
        Genera un embedding de texto
        
        Args:
            text: Texto a embedar
            model: Modelo de embedding (default: text-embedding-3-small)
        
        Returns:
            Lista con el vector de embedding
        """
        model = model or os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        
        response = self.client.embeddings.create(
            model=model,
            input=text
        )
        
        return response.data[0].embedding

