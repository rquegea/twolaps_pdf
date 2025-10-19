"""
Strategic Agent
Generación de oportunidades y riesgos estratégicos
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, List
from src.analytics.agents.base_agent import BaseAgent
from src.database.models import AnalysisResult
from src.query_executor.api_clients import OpenAIClient


class StrategicAgent(BaseAgent):
    """
    Agente estratégico
    Genera oportunidades y riesgos basándose en análisis previos usando LLM
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
                self.task_prompt = prompts.get('strategic_agent', {}).get('task', '')
    
    def analyze(self, categoria_id: int, periodo: str) -> Dict[str, Any]:
        """
        Genera oportunidades y riesgos usando LLM con acceso a respuestas textuales
        
        Args:
            categoria_id: ID de categoría
            periodo: Periodo (YYYY-MM)
        
        Returns:
            Dict con oportunidades y riesgos
        """
        # Leer análisis previos
        quantitative = self._get_analysis('quantitative', categoria_id, periodo)
        sentiment = self._get_analysis('sentiment', categoria_id, periodo)
        competitive = self._get_analysis('competitive', categoria_id, periodo)
        trends = self._get_analysis('trends', categoria_id, periodo)
        
        if not quantitative or not sentiment:
            return {'error': 'Faltan análisis previos'}
        
        # NUEVO: Obtener muestra de respuestas textuales originales
        raw_responses = self._get_raw_responses_sample(categoria_id, periodo, sample_size=10)
        
        # Construir prompt con datos estructurados Y respuestas textuales
        prompt = self.task_prompt.format(
            sov_data=json.dumps(quantitative.get('sov_percent', {}), indent=2),
            sentiment_data=json.dumps(sentiment.get('por_marca', {}), indent=2),
            competitive_data=json.dumps(competitive, indent=2),
            trends_data=json.dumps(trends.get('tendencias', []), indent=2),
            raw_responses_sample=raw_responses
        )
        
        # Llamar a LLM
        try:
            result = self.client.generate(
                prompt=prompt,
                temperature=0.4,
                max_tokens=3000,
                json_mode=True
            )
            
            # Parsear JSON
            strategic_insights = json.loads(result['response_text'])
            
            resultado = {
                'periodo': periodo,
                'categoria_id': categoria_id,
                'oportunidades': strategic_insights.get('oportunidades', []),
                'riesgos': strategic_insights.get('riesgos', [])
            }
            
            self.save_results(categoria_id, periodo, resultado)
            return resultado
            
        except Exception as e:
            self.logger.error(f"Error generando análisis estratégico: {e}", exc_info=True)
            return {'error': f'Error en análisis estratégico: {str(e)}'}
    
    def _get_analysis(self, agent_name: str, categoria_id: int, periodo: str) -> Dict:
        """Helper para obtener análisis"""
        result = self.session.query(AnalysisResult).filter_by(
            categoria_id=categoria_id,
            periodo=periodo,
            agente=agent_name
        ).first()
        
        return result.resultado if result else {}
    
    def _get_raw_responses_sample(self, categoria_id: int, periodo: str, sample_size: int = 10) -> str:
        """
        Obtiene una muestra representativa de respuestas textuales originales
        
        Args:
            categoria_id: ID de categoría
            periodo: Periodo (YYYY-MM)
            sample_size: Número de respuestas a incluir
        
        Returns:
            String formateado con las respuestas textuales
        """
        from src.database.models import Query, QueryExecution
        from sqlalchemy import extract
        
        year, month = map(int, periodo.split('-'))
        
        # Obtener ejecuciones del periodo
        executions = self.session.query(QueryExecution).join(
            Query
        ).filter(
            Query.categoria_id == categoria_id,
            extract('month', QueryExecution.timestamp) == month,
            extract('year', QueryExecution.timestamp) == year,
            QueryExecution.respuesta_texto.isnot(None)
        ).limit(sample_size).all()
        
        if not executions:
            return "No hay respuestas textuales disponibles para este periodo."
        
        # Formatear respuestas
        formatted_responses = []
        for i, execution in enumerate(executions, 1):
            # Limitar longitud de cada respuesta para no exceder límites de tokens
            texto_truncado = execution.respuesta_texto[:800] if execution.respuesta_texto else ""
            formatted_responses.append(
                f"--- RESPUESTA {i} ---\n"
                f"Query: {execution.query.pregunta if execution.query else 'N/A'}\n"
                f"Contenido: {texto_truncado}\n"
            )
        
        return "\n".join(formatted_responses)

