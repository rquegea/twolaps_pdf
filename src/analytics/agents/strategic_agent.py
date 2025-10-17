"""
Strategic Agent
Generación de oportunidades y riesgos estratégicos
"""

from typing import Dict, Any, List
from src.analytics.agents.base_agent import BaseAgent
from src.database.models import AnalysisResult


class StrategicAgent(BaseAgent):
    """
    Agente estratégico
    Genera oportunidades y riesgos basándose en análisis previos
    """
    
    def analyze(self, categoria_id: int, periodo: str) -> Dict[str, Any]:
        """
        Genera oportunidades y riesgos
        
        Args:
            categoria_id: ID de categoría
            periodo: Periodo (YYYY-MM)
        
        Returns:
            Dict con oportunidades y riesgos
        """
        # Obtener todos los análisis previos
        competitive = self._get_analysis('competitive', categoria_id, periodo)
        trends = self._get_analysis('trends', categoria_id, periodo)
        sentiment = self._get_analysis('sentiment', categoria_id, periodo)
        
        if not competitive:
            return {'error': 'Faltan análisis previos'}
        
        # Generar oportunidades
        oportunidades = self._identify_opportunities(competitive, trends, sentiment)
        
        # Generar riesgos
        riesgos = self._identify_risks(competitive, trends, sentiment)
        
        resultado = {
            'periodo': periodo,
            'categoria_id': categoria_id,
            'oportunidades': oportunidades,
            'riesgos': riesgos,
            'quick_wins': self._identify_quick_wins(oportunidades)
        }
        
        self.save_results(categoria_id, periodo, resultado)
        return resultado
    
    def _get_analysis(self, agent_name: str, categoria_id: int, periodo: str) -> Dict:
        """Helper para obtener análisis"""
        result = self.session.query(AnalysisResult).filter_by(
            categoria_id=categoria_id,
            periodo=periodo,
            agente=agent_name
        ).first()
        
        return result.resultado if result else {}
    
    def _identify_opportunities(self, competitive: Dict, trends: Dict, sentiment: Dict) -> List[Dict]:
        """Identifica oportunidades"""
        opportunities = []
        
        # Oportunidad 1: Gaps competitivos
        for gap in competitive.get('gaps_competitivos', []):
            if gap['gap_type'] == 'oportunidad':
                opportunities.append({
                    'titulo': f"Aprovechar posicionamiento de {gap['marca']}",
                    'descripcion': gap['razon'],
                    'prioridad': 'alta',
                    'impacto': 'alto',
                    'esfuerzo': 'medio'
                })
        
        # Oportunidad 2: Tendencias positivas
        for tendencia in trends.get('tendencias', []):
            if tendencia['cambio_puntos'] > 10:
                opportunities.append({
                    'titulo': f"Capitalizar crecimiento de {tendencia['marca']}",
                    'descripcion': f"SOV aumentó {tendencia['cambio_puntos']:.1f} puntos",
                    'prioridad': 'media',
                    'impacto': 'medio',
                    'esfuerzo': 'bajo'
                })
        
        # Limitar a top 5
        return opportunities[:5]
    
    def _identify_risks(self, competitive: Dict, trends: Dict, sentiment: Dict) -> List[Dict]:
        """Identifica riesgos"""
        risks = []
        
        # Riesgo 1: Gaps de riesgo
        for gap in competitive.get('gaps_competitivos', []):
            if gap['gap_type'] == 'riesgo':
                risks.append({
                    'titulo': f"Deterioro de reputación de {gap['marca']}",
                    'descripcion': gap['razon'],
                    'probabilidad': 'alta',
                    'severidad': 'alta',
                    'mitigacion': "Mejorar comunicación y atributos de producto"
                })
        
        # Riesgo 2: Tendencias negativas
        for tendencia in trends.get('tendencias', []):
            if tendencia['cambio_puntos'] < -10:
                risks.append({
                    'titulo': f"Pérdida de share of voice de {tendencia['marca']}",
                    'descripcion': f"SOV cayó {abs(tendencia['cambio_puntos']):.1f} puntos",
                    'probabilidad': 'media',
                    'severidad': 'media',
                    'mitigacion': "Revisar estrategia de visibilidad"
                })
        
        return risks[:5]
    
    def _identify_quick_wins(self, opportunities: List[Dict]) -> List[Dict]:
        """Identifica quick wins"""
        return [
            opp for opp in opportunities
            if opp.get('esfuerzo') == 'bajo' and opp.get('impacto') in ['alto', 'medio']
        ][:3]

