"""
Base AI Client
Interfaz abstracta para todos los clientes de APIs de IA
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
import time


class BaseAIClient(ABC):
    """
    Clase base abstracta para clientes de APIs de IA
    Todos los proveedores deben implementar esta interfaz
    """
    
    def __init__(self, api_key: str, model: str):
        """
        Initialize client
        
        Args:
            api_key: API key para el proveedor
            model: Modelo a usar
        """
        self.api_key = api_key
        self.model = model
        self.provider_name = self.__class__.__name__.replace('Client', '').lower()
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        json_mode: bool = False
    ) -> Dict:
        """
        Genera una respuesta usando el modelo
        
        Args:
            prompt: Texto del prompt
            temperature: Temperatura para generación (0-1)
            max_tokens: Máximo de tokens a generar
        
        Returns:
            Dict con:
                - response_text: Texto de la respuesta
                - tokens_input: Tokens de entrada
                - tokens_output: Tokens de salida
                - model: Modelo usado
                - latency_ms: Latencia en milisegundos
        """
        pass
    
    def execute_query(
        self,
        question: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        json_mode: bool = False
    ) -> Dict:
        """
        Ejecuta una query/pregunta y mide métricas
        
        Args:
            question: Pregunta a hacer
            temperature: Temperatura
            max_tokens: Máximo de tokens
        
        Returns:
            Dict con respuesta y métricas
        """
        start_time = time.time()
        
        try:
            result = self.generate(
                prompt=question,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            result['latency_ms'] = latency_ms
            result['provider'] = self.provider_name
            result['success'] = True
            result['error'] = None
            
            return result
        
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return {
                'response_text': '',
                'tokens_input': 0,
                'tokens_output': 0,
                'model': self.model,
                'latency_ms': latency_ms,
                'provider': self.provider_name,
                'success': False,
                'error': str(e)
            }
    
    def get_provider_name(self) -> str:
        """Retorna el nombre del proveedor"""
        return self.provider_name
    
    def get_model_name(self) -> str:
        """Retorna el nombre del modelo"""
        return self.model

