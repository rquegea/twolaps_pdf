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
from src.query_executor.api_clients import AnthropicClient


class StrategicAgent(BaseAgent):
    """
    Agente estratégico
    Genera oportunidades y riesgos basándose en análisis previos usando LLM
    """
    
    def __init__(self, session, version: str = "1.0.0"):
        super().__init__(session, version)
        self.client = AnthropicClient()  # Cambiado a Anthropic
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
        qualitative = self._get_analysis('qualitative', categoria_id, periodo)
        if not qualitative:
            qualitative = self._get_analysis('qualitativeextraction', categoria_id, periodo)
        competitive = self._get_analysis('competitive', categoria_id, periodo)
        trends = self._get_analysis('trends', categoria_id, periodo)
        # Datos adicionales FMCG usados por el prompt estratégico ampliado
        campaign = self._get_analysis('campaign_analysis', categoria_id, periodo)
        channel = self._get_analysis('channel_analysis', categoria_id, periodo)
        esg = self._get_analysis('esg_analysis', categoria_id, periodo)
        packaging = self._get_analysis('packaging_analysis', categoria_id, periodo)
        
        if not quantitative or not qualitative:
            return {'error': 'Faltan análisis previos'}
        
        # NUEVO: Obtener muestra estratificada de respuestas textuales
        raw_responses = self._get_stratified_sample(categoria_id, periodo, samples_per_group=2)
        
        # Construir prompt con datos estructurados Y respuestas textuales
        prompt = self.task_prompt.format(
            sov_data=json.dumps(quantitative.get('sov_percent', {}), indent=2),
            sentiment_data=json.dumps(qualitative.get('sentimiento_por_marca', {}), indent=2),
            competitive_data=json.dumps(competitive, indent=2),
            trends_data=json.dumps(trends.get('tendencias', []), indent=2),
            raw_responses_sample=raw_responses,
            # Campos FMCG adicionales requeridos por el prompt YAML
            campaign_analysis_data=json.dumps(campaign, indent=2),
            channel_analysis_data=json.dumps(channel, indent=2),
            esg_analysis_data=json.dumps(esg, indent=2),
            packaging_analysis_data=json.dumps(packaging, indent=2)
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

