"""
Sentiment Agent
Análisis de sentimiento usando LLM
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any
from collections import defaultdict
from sqlalchemy import extract
from src.analytics.agents.base_agent import BaseAgent
from src.database.models import Query, QueryExecution, Marca
from src.query_executor.api_clients import OpenAIClient


class SentimentAgent(BaseAgent):
    """
    Agente de análisis de sentimiento
    Usa LLM para clasificar sentimiento por marca y atributo
    """
    
    def __init__(self, session, version: str = "1.0.0"):
        super().__init__(session, version)
        self.client = OpenAIClient()
        self.load_prompts()
    
    def load_prompts(self):
        """Carga prompts de configuración"""
        prompt_path = Path("config/prompts/agent_prompts.yaml")
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompts = yaml.safe_load(f)
                self.task_prompt = prompts.get('sentiment_agent', {}).get('task', '')
        else:
            self.task_prompt = self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        """Prompt por defecto si no hay config"""
        return """
        Analiza el sentimiento sobre las marcas en el siguiente texto.
        
        MARCAS A ANALIZAR: {marcas}
        
        TEXTO: {texto}
        
        Devuelve JSON:
        {{
          "marca": {{
            "score": float (-1 a 1),
            "tono": "positivo|neutral|negativo",
            "atributos": {{"sabor": score, "precio": score, "calidad": score}},
            "quote": "fragmento relevante"
          }}
        }}
        """
    
    def analyze(self, categoria_id: int, periodo: str) -> Dict[str, Any]:
        """
        Ejecuta análisis de sentimiento
        
        Args:
            categoria_id: ID de categoría
            periodo: Periodo (YYYY-MM)
        
        Returns:
            Dict con análisis de sentimiento
        """
        # Ventana temporal dinámica
        start, end, _ = self._parse_periodo(periodo)
        
        # 1. Obtener marcas
        marcas = self.session.query(Marca).filter_by(
            categoria_id=categoria_id
        ).all()
        
        if not marcas:
            return {'error': 'No hay marcas configuradas'}
        
        marca_nombres = [m.nombre for m in marcas]
        
        # 2. Obtener ejecuciones
        executions = self.session.query(QueryExecution).join(
            Query
        ).filter(
            Query.categoria_id == categoria_id,
            QueryExecution.timestamp >= start,
            QueryExecution.timestamp < end
        ).all()
        
        if not executions:
            return {'error': 'No hay datos para analizar'}
        
        # 3. Analizar sentimiento por respuesta (muestra)
        # Para evitar costes excesivos, analizamos una muestra
        sample_size = min(20, len(executions))
        sampled_executions = executions[:sample_size]
        
        sentiments_by_marca = defaultdict(list)
        atributos_by_marca = defaultdict(lambda: defaultdict(list))
        
        for execution in sampled_executions:
            # Construir prompt
            prompt = self.task_prompt.format(
                marcas=', '.join(marca_nombres),
                texto=execution.respuesta_texto[:1500]  # Limitar texto
            )
            
            try:
                # Llamar a LLM
                result = self.client.generate(
                    prompt=prompt,
                    temperature=0.3,
                    max_tokens=1000
                )
                
                # Parsear respuesta JSON
                sentiment_data = json.loads(result['response_text'])
                
                # Agregar resultados
                for marca, data in sentiment_data.items():
                    if marca in marca_nombres:
                        sentiments_by_marca[marca].append(data.get('score', 0))
                        
                        # Atributos
                        for attr, score in data.get('atributos', {}).items():
                            atributos_by_marca[marca][attr].append(score)
            
            except Exception as e:
                # Si falla el parsing, continuar con siguiente
                continue
        
        # 4. Agregar sentimientos
        sentimiento_agregado = {}
        for marca in marca_nombres:
            scores = sentiments_by_marca.get(marca, [0])
            sentimiento_agregado[marca] = {
                'score_medio': sum(scores) / len(scores) if scores else 0,
                'menciones_analizadas': len(scores),
                'distribucion': {
                    'positivo': len([s for s in scores if s > 0.3]),
                    'neutral': len([s for s in scores if -0.3 <= s <= 0.3]),
                    'negativo': len([s for s in scores if s < -0.3])
                }
            }
        
        # 5. Agregar atributos
        atributos_agregados = {}
        for marca in marca_nombres:
            atributos_agregados[marca] = {}
            for attr, scores in atributos_by_marca.get(marca, {}).items():
                atributos_agregados[marca][attr] = sum(scores) / len(scores) if scores else 0
        
        # 6. Resultado
        resultado = {
            'periodo': periodo,
            'categoria_id': categoria_id,
            'sentimiento_global': sum(
                s['score_medio'] for s in sentimiento_agregado.values()
            ) / len(sentimiento_agregado) if sentimiento_agregado else 0,
            'por_marca': sentimiento_agregado,
            'atributos_por_marca': atributos_agregados,
            'metadata': {
                'executions_analizadas': sample_size,
                'total_executions': len(executions),
                'metodo': 'llm_sampling'
            }
        }
        
        # Guardar
        self.save_results(categoria_id, periodo, resultado)
        
        return resultado

