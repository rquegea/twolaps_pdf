"""
Competitive Agent
Análisis de posicionamiento competitivo
"""

from typing import Dict, Any
from src.analytics.agents.base_agent import BaseAgent
from src.database.models import AnalysisResult


class CompetitiveAgent(BaseAgent):
    """
    Agente de análisis competitivo
    Lee resultados de agentes previos y genera análisis comparativo
    """
    
    def analyze(self, categoria_id: int, periodo: str) -> Dict[str, Any]:
        """
        Analiza posicionamiento competitivo
        
        Args:
            categoria_id: ID de categoría
            periodo: Periodo (YYYY-MM)
        
        Returns:
            Dict con análisis competitivo
        """
        # Obtener análisis previos
        quantitative = self._get_analysis('quantitative', categoria_id, periodo)
        qualitative = self._get_analysis('qualitative', categoria_id, periodo)
        # Fallback por compatibilidad con versiones previas
        if not qualitative:
            qualitative = self._get_analysis('qualitativeextraction', categoria_id, periodo)
        
        if not quantitative or not qualitative:
            return {'error': 'Faltan análisis previos (quantitative y qualitative)'}
        
        # Análisis competitivo
        sov = quantitative.get('sov_percent', {})
        sentimientos = qualitative.get('sentimiento_por_marca', {})
        
        # Identificar líder
        lider = max(sov.items(), key=lambda x: x[1])[0] if sov else None
        
        # Gaps competitivos (marcas con bajo SOV pero alto sentimiento)
        gaps = []
        for marca in sov.keys():
            sov_val = sov.get(marca, 0)
            sent_val = sentimientos.get(marca, {}).get('score_medio', 0)
            
            if sov_val < 15 and sent_val > 0.5:
                gaps.append({
                    'marca': marca,
                    'gap_type': 'oportunidad',
                    'razon': f"Alto sentimiento ({sent_val:.2f}) pero bajo SOV ({sov_val:.1f}%)"
                })
            elif sov_val > 25 and sent_val < 0.3:
                gaps.append({
                    'marca': marca,
                    'gap_type': 'riesgo',
                    'razon': f"Alto SOV ({sov_val:.1f}%) pero sentimiento bajo ({sent_val:.2f})"
                })
        
        resultado = {
            'periodo': periodo,
            'categoria_id': categoria_id,
            'lider_mercado': lider,
            'sov_lider': sov.get(lider, 0) if lider else 0,
            'gaps_competitivos': gaps,
            'comparativa': {
                marca: {
                    'sov': sov.get(marca, 0),
                    'sentimiento': sentimientos.get(marca, {}).get('score_medio', 0),
                    'posicion': 'lider' if marca == lider else 'seguidor'
                }
                for marca in sov.keys()
            }
        }
        
        self.save_results(categoria_id, periodo, resultado)
        return resultado
    
    def _get_analysis(self, agent_name: str, categoria_id: int, periodo: str) -> Dict:
        """Helper para obtener análisis previo"""
        result = self.session.query(AnalysisResult).filter_by(
            categoria_id=categoria_id,
            periodo=periodo,
            agente=agent_name
        ).first()
        
        return result.resultado if result else {}

