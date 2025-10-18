"""
Google Client
Cliente para Google Generative AI (Gemini)
"""

import os
from typing import Dict, Optional
import google.generativeai as genai
from src.query_executor.api_clients.base import BaseAIClient


class GoogleClient(BaseAIClient):
    """Cliente para la API de Google Generative AI (Gemini)"""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Google client
        
        Args:
            api_key: API key (si None, se lee de env)
            model: Modelo a usar (si None, se lee de env)
        """
        api_key = api_key or os.getenv("GOOGLE_API_KEY")
        model = model or os.getenv("GOOGLE_MODEL", "gemini-1.5-pro-latest")

        # Normalizar alias y prefijos comunes para evitar 404 por nombre de modelo
        alias_map = {
            "gemini-1.5-pro": "gemini-1.5-pro-latest",
            "models/gemini-1.5-pro": "gemini-1.5-pro-latest",
            "models/gemini-1.5-pro-latest": "gemini-1.5-pro-latest",
            "models/gemini-2.0-flash": "gemini-2.0-flash",
            "models/gemini-2.0-flash-latest": "gemini-2.0-flash-latest",
            "models/gemini-2.5-flash": "gemini-2.5-flash",
            "models/gemini-2.5-flash-latest": "gemini-2.5-flash-latest",
        }
        model = alias_map.get(model, model)
        
        super().__init__(api_key, model)
        
        genai.configure(api_key=api_key)
        self.model_instance = genai.GenerativeModel(model)
    
    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Dict:
        """
        Genera una respuesta usando Gemini
        
        Args:
            prompt: Texto del prompt
            temperature: Temperatura (0-1)
            max_tokens: Máximo de tokens (max_output_tokens en Gemini)
        
        Returns:
            Dict con respuesta y métricas
        """
        generation_config = {
            "temperature": temperature,
        }
        
        if max_tokens:
            generation_config["max_output_tokens"] = max_tokens
        
        response = self.model_instance.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        # Google no siempre provee token counts detallados
        # Estimamos basándonos en la longitud del texto
        tokens_input = len(prompt.split()) * 1.3  # Estimación aproximada
        tokens_output = len(response.text.split()) * 1.3 if response.text else 0
        
        return {
            'response_text': response.text if response.text else '',
            'tokens_input': int(tokens_input),
            'tokens_output': int(tokens_output),
            'model': self.model
        }

