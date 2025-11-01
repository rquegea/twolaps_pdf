"""
Anthropic Client
Cliente para Anthropic (Claude)
"""

import os
from typing import Dict, Optional, List
from anthropic import Anthropic, NotFoundError
from anthropic._exceptions import RateLimitError
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
        # Modelo por defecto actualizado a la versión "latest"
        model = model or os.getenv("ANTHROPIC_MODEL", "claude-3-7-sonnet-latest")
        
        super().__init__(api_key, model)
        
        # Inicializa cliente Anthropic
        self.client = Anthropic(api_key=api_key)
        
        # Mapeo de versiones antiguas a modelos que funcionan
        model_aliases = {
            "claude-3-5-sonnet-20240620": "claude-3-7-sonnet-latest",
            "claude-3-5-sonnet-20241022": "claude-3-7-sonnet-latest",
            "claude-3-5-sonnet-20240229": "claude-3-7-sonnet-latest",
            "claude-3-sonnet-20240229": "claude-3-7-sonnet-latest",
        }
        # Normalizar modelo si es una versión antigua
        self.model = model_aliases.get(self.model, self.model)
        
        # Modelos de respaldo en caso de 404/not_found (en orden de preferencia)
        # Solo incluimos modelos que sabemos que funcionan
        self._fallback_models: List[str] = [
            m for m in [
                self.model,
                "claude-3-7-sonnet-latest",    # Modelo principal que funciona
                "claude-3-5-sonnet-latest",    # Latest pointer (backup)
                "claude-3-opus-latest",        # Opus latest (backup)
            ] if m is not None
        ]
    
    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        json_mode: bool = False
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
        
        # Intento con fallback de modelos si el modelo configurado no existe (404)
        last_error: Optional[Exception] = None
        for candidate_model in self._fallback_models:
            try:
                # Compatibilidad: algunos entornos exponen client.completions (sin messages)
                if hasattr(self.client, "messages"):
                    kwargs = {
                        "model": candidate_model,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ]
                    }
                    # Intentar JSON mode si se solicita
                    if json_mode:
                        try:
                            kwargs["response_format"] = {"type": "json"}
                        except Exception:
                            # Si la SDK no soporta response_format, seguimos sin él
                            pass

                    try:
                        response = self.client.messages.create(**kwargs)
                    except RateLimitError:
                        # Fallback inmediato a OpenAI si Anthropic limita por tasa
                        from src.query_executor.api_clients.openai_client import OpenAIClient
                        oc = OpenAIClient()
                        return oc.generate(prompt=prompt, temperature=temperature, max_tokens=min(max_tokens, 1500))
                    return {
                        'response_text': response.content[0].text if getattr(response, 'content', None) else '',
                        'tokens_input': getattr(getattr(response, 'usage', None), 'input_tokens', 0),
                        'tokens_output': getattr(getattr(response, 'usage', None), 'output_tokens', 0),
                        'model': candidate_model
                    }
                else:
                    # Fallback a completions API
                    import anthropic as _anth
                    resp = self.client.completions.create(
                        model=candidate_model,
                        max_tokens_to_sample=max_tokens,
                        temperature=temperature,
                        prompt=f"{_anth.HUMAN_PROMPT} {prompt}{_anth.AI_PROMPT}",
                    )
                    text = getattr(resp, 'completion', '')
                    return {
                        'response_text': text,
                        'tokens_input': 0,
                        'tokens_output': 0,
                        'model': candidate_model
                    }
            except NotFoundError as e:
                # Probar siguiente modelo si el actual no existe
                last_error = e
                continue
        # Si agotamos todos los modelos de respaldo, relanzar el último error (habitualmente NotFoundError)
        if last_error:
            raise last_error
        # Devolver error genérico si no hubo excepción pero tampoco retorno (no debería ocurrir)
        raise RuntimeError("No se pudo generar respuesta con Anthropic")

