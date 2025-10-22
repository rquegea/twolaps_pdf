"""
Attributes Agent
Extracción de atributos FMCG específicos
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any
from collections import defaultdict
from sqlalchemy import extract
from src.analytics.agents.base_agent import BaseAgent
from src.database.models import Query, QueryExecution, Marca
from src.query_executor.api_clients import AnthropicClient


class AttributesAgent(BaseAgent):
    """
    Agente de extracción de atributos
    Identifica atributos asociados a marcas (sabor, precio, calidad, etc.)
    """
    
    def __init__(self, session, version: str = "1.0.0"):
        super().__init__(session, version)
        self.client = AnthropicClient()
    
    def analyze(self, categoria_id: int, periodo: str) -> Dict[str, Any]:
        """
        Extrae atributos de las marcas
        
        Args:
            categoria_id: ID de categoría
            periodo: Periodo (YYYY-MM)
        
        Returns:
            Dict con atributos por marca
        """
        year, month = map(int, periodo.split('-'))
        
        # Obtener marcas
        marcas = self.session.query(Marca).filter_by(
            categoria_id=categoria_id
        ).all()
        
        if not marcas:
            return {'error': 'No hay marcas configuradas'}
        
        marca_nombres = [m.nombre for m in marcas]
        
        # Obtener ejecuciones (muestra)
        executions = self.session.query(QueryExecution).join(
            Query
        ).filter(
            Query.categoria_id == categoria_id,
            extract('month', QueryExecution.timestamp) == month,
            extract('year', QueryExecution.timestamp) == year
        ).limit(15).all()
        
        if not executions:
            return {'error': 'No hay datos para analizar'}
        
        # Analizar atributos
        atributos_por_marca = defaultdict(lambda: defaultdict(int))
        
        for execution in executions:
            prompt = f"""
            Extrae atributos asociados a estas marcas: {', '.join(marca_nombres)}
            
            Texto: {execution.respuesta_texto[:1200]}
            
            Atributos FMCG a identificar:
            - Calidad: premium, estándar, económica
            - Precio: caro, accesible, económico
            - Sabor: intenso, suave, equilibrado
            - Ocasión: celebración, cotidiano, regalo
            
            Devuelve JSON: {{"marca": {{"calidad": [...], "precio": [...], "sabor": [...], "ocasion": [...]}}}}
            """
            
            try:
                result = self.client.generate(prompt=prompt, temperature=0.3, max_tokens=800)
                data = json.loads(result['response_text'])
                
                for marca, attrs in data.items():
                    if marca in marca_nombres:
                        for categoria_attr, valores in attrs.items():
                            for valor in valores:
                                atributos_por_marca[marca][f"{categoria_attr}:{valor}"] += 1
            
            except Exception:
                continue
        
        # Resultado
        resultado = {
            'periodo': periodo,
            'categoria_id': categoria_id,
            'atributos_por_marca': {
                marca: dict(attrs) for marca, attrs in atributos_por_marca.items()
            },
            'metadata': {
                'executions_analizadas': len(executions)
            }
        }
        
        self.save_results(categoria_id, periodo, resultado)
        return resultado

